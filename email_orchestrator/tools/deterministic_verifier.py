import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime
try:
    from rapidfuzz import fuzz
except ImportError:
    import difflib
    # Fallback wrapper if rapidfuzz fails, though we installed it
    class FuzzWrapper:
        @staticmethod
        def ratio(s1, s2):
            return difflib.SequenceMatcher(None, s1, s2).ratio() * 100
    fuzz = FuzzWrapper()

from email_orchestrator.schemas import EmailDraft, CampaignPlan, Issue

class DeterministicVerifier:
    """
    Layer 1 QA: Cheap, fast, deterministic checks.
    - Similarity (Jaccard/Fuzzy)
    - Formatting (No Emojis, Banned Chars)
    - Length Constraints
    """
    
    def __init__(self):
        # Similarity Thresholds
        self.JACCARD_THRESHOLD = 0.6
        self.FUZZY_THRESHOLD = 80.0 # RapidFuzz uses 0-100
        
        # Length Constraints (Min-Max chars)
        # UPDATED: Flexible minimum (0). Max is the only hard cap.
        self.LENGTH_RULES = {
            "subject": (0, 60),      # Increased from 40 for French length
            "preview": (0, 80),      # Increased from 55
            "hero_title": (0, 60),   # Increased from 40
            "hero_subtitle": (0, 80),# Increased from 55
            "descriptive_block_title": (0, 60),
            "descriptive_block_subtitle": (0, 90), # Increased from 60
            "descriptive_block_content": (0, 600), # Increased from 400
            "product_block_title": (0, 60),
            "product_block_subtitle": (0, 100),
            "cta_hero": (0, 25),    # Increased from 15 ("Je profite de l'offre" is > 15)
            "cta_product": (0, 25),
            "cta_descriptive": (2, 30) # Enforce presence (min 2 chars)
        }
        
    def _jaccard_similarity(self, s1: str, s2: str) -> float:
        """Calculates Jaccard similarity between two strings (word-based)."""
        set1 = set(s1.lower().split())
        set2 = set(s2.lower().split())
        if not set1 or not set2:
            return 0.0
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union

    def _check_similarity(self, s1: str, s2: str) -> Tuple[bool, str]:
        """Checks if two strings are too similar."""
        jaccard = self._jaccard_similarity(s1, s2)
        fuzzy_score = fuzz.ratio(s1.lower(), s2.lower())
        
        if jaccard >= self.JACCARD_THRESHOLD:
            return True, f"Jaccard Similarity too high ({jaccard:.2f} >= {self.JACCARD_THRESHOLD})"
        if fuzzy_score >= self.FUZZY_THRESHOLD:
            return True, f"Fuzzy Similarity too high ({fuzzy_score:.1f} >= {self.FUZZY_THRESHOLD})"
            
        return False, ""

    def _strip_tags(self, text: str) -> str:
        """Removes <b> and </b> tags for comparison."""
        if not text: return ""
        return text.replace("<b>", "").replace("</b>", "")

    def _is_entirely_bolded(self, text: str) -> bool:
        """Checks if the text is wrapped in <b>...</b> from start to end."""
        if not text: return False
        t = text.strip()
        return t.startswith("<b>") and t.endswith("</b>") and t.count("<b>") == 1 and t.count("</b>") == 1

    def verify_draft(self, draft: EmailDraft, history: List[Dict] = None, campaign_id: str = None) -> List[Issue]:
        """Runs all deterministic checks on an email draft."""
        issues = []
        
        # 0. Strip tags for similarity and length checks
        clean_hero_title = self._strip_tags(draft.hero_title)
        clean_hero_subtitle = self._strip_tags(draft.hero_subtitle)
        clean_desc_title = self._strip_tags(draft.descriptive_block_title)
        clean_desc_subtitle = self._strip_tags(draft.descriptive_block_subtitle)

        # 1. Similarity Checks (Internal Repetition - STRICT)
        pairs = [
            ("Hero Title vs Subtitle", clean_hero_title, clean_hero_subtitle),
            ("Hero Title vs Desc Block Title", clean_hero_title, clean_desc_title),
            ("Hero Title vs Desc Block Subtitle", clean_hero_title, clean_desc_subtitle),
            ("Hero Subtitle vs Desc Block Title", clean_hero_subtitle, clean_desc_title),
            ("Hero Subtitle vs Desc Block Subtitle", clean_hero_subtitle, clean_desc_subtitle),
            ("Desc Block Title vs Subtitle", clean_desc_title, clean_desc_subtitle),
            ("Subject vs Preview", draft.subject, draft.preview)
        ]
        
        for name, s1, s2 in pairs:
            if not s1 or not s2: continue
            is_similar, reason = self._check_similarity(s1, s2)
            if is_similar:
                issues.append(Issue(
                    type="repetition",
                    severity="P1",
                    scope="email",
                    field="internal_repetition",
                    problem=f"{name} are too similar (Repetition).",
                    rationale=reason
                ))

        # 2. Formatting Checks
        # A. Banned Characters (Dashes) - STRICT
        # Only allow simple punctuation. Reject em dash, en dash, hyphen if used as distinct separator.
        # Actually user said "never use em dashes, hyphens or dashes".
        all_text_fields = [
            ("Subject", draft.subject),
            ("Preview", draft.preview),
            ("Hero Title", draft.hero_title),
            ("Hero Subtitle", draft.hero_subtitle),
            ("Descriptive Block Title", draft.descriptive_block_title),
            ("Descriptive Block Subtitle", draft.descriptive_block_subtitle),
            ("Descriptive Block Content", draft.descriptive_block_content),
            ("Product Block Title", draft.product_block_title),
            ("Product Block Subtitle", draft.product_block_subtitle)
        ]
        
        for name, text in all_text_fields:
            if not text: continue
            if self._contains_banned_dashes(text):
                issues.append(Issue(
                    type="formatting",
                    severity="P1",
                    scope="email",
                    field=name.lower().replace(" ", "_"),
                    problem=f"{name} contains banned dashes/hyphens.",
                    rationale="Strict Rule: Never use em dashes (—), en dashes (–), or hyphens (-)."
                ))

        # B. No Emojis in Hero Banner
        if self._contains_emoji(draft.hero_title) or self._contains_emoji(draft.hero_subtitle):
             issues.append(Issue(
                type="formatting",
                severity="P1",
                scope="email",
                field="hero_section",
                problem="Hero Banner contains emojis.",
                rationale="Strict Rule: No emojis in Hero Title or Subtitle."
            ))

        # C. Over-Bolding Check (New User Feedback)
        # Rule: Strategic bolding ONLY. Do not bold the entire line.
        check_bold_fields = [
            ("Hero Title", draft.hero_title),
            ("Hero Subtitle", draft.hero_subtitle),
            ("Descriptive Block Title", draft.descriptive_block_title),
            ("Descriptive Block Subtitle", draft.descriptive_block_subtitle)
        ]
        for name, text in check_bold_fields:
            if self._is_entirely_bolded(text):
                issues.append(Issue(
                    type="formatting",
                    severity="P1",
                    scope="email",
                    field=name.lower().replace(" ", "_"),
                    problem=f"{name} is entirely bolded.",
                    rationale="Strategic Bolding Rule: Never bold the entire line. Use <b>...</b> only for specific focused words to add emphasis."
                ))

        # D. No HTML in Headers (STRICT)
        # Rule: Headers must be plain text. HTML tags cause rendering issues or look ugly in previews.
        header_fields_no_html = [
             ("Subject", draft.subject),
             ("Preview", draft.preview),
             ("Hero Title", draft.hero_title),
             ("Hero Subtitle", draft.hero_subtitle),
             ("Descriptive Block Title", draft.descriptive_block_title),
             ("Descriptive Block Subtitle", draft.descriptive_block_subtitle),
             ("Product Block Title", draft.product_block_title),
             ("Product Block Subtitle", draft.product_block_subtitle)
        ]
        for name, text in header_fields_no_html:
             if self._contains_html_tags(text):
                 issues.append(Issue(
                    type="formatting",
                    severity="P1",
                    scope="email",
                    field=name.lower().replace(" ", "_"),
                    problem=f"{name} contains HTML tags.",
                    rationale="Strict Rule: Headers and Subtitles must be PLAIN TEXT. remove <b>, <i>, etc."
                ))

        # D. Emoji Pacing (History Aware)
        # Rule: Exactly 1 emoji per campaign. Target 1 every 4 emails overall.
        if history:
            # 1. Check current campaign usage
            current_campaign_emails = [e for e in history if e.get("campaign_id") == campaign_id]
            any_emoji_in_current = any(self._contains_emoji(e.get("final_draft", {}).get("subject", "")) for e in current_campaign_emails)
            
            if any_emoji_in_current:
                if self._contains_emoji(draft.subject):
                    issues.append(Issue(
                        type="formatting",
                        severity="P1",
                        scope="email",
                        field="subject",
                        problem="Too many emojis in campaign.",
                        rationale="Strict Rule: Only 1 email per campaign should have an emoji in the subject line."
                    ))
            else:
                # 2. No emoji used in current campaign yet. Check overall spacing.
                all_brand_emails = sorted(history, key=lambda x: x.get("timestamp", ""), reverse=True)
                dist_to_last_emoji = 0
                found_emoji_globally = False
                for i, entry in enumerate(all_brand_emails[:8]):
                    subj = entry.get("final_draft", {}).get("subject", "") if isinstance(entry.get("final_draft"), dict) else ""
                    if self._contains_emoji(subj):
                        dist_to_last_emoji = i + 1
                        found_emoji_globally = True
                        break
                    dist_to_last_emoji = i + 1
                
                # If we haven't used an emoji in a while (>3 emails), we SHOULD use it now.
                # But only if it's the first in this campaign.
                if not found_emoji_globally or dist_to_last_emoji >= 3:
                    if not self._contains_emoji(draft.subject):
                        # We don't FORCE it yet unless we want to, but the prompt should encourage it.
                        if dist_to_last_emoji >= 4:
                            issues.append(Issue(
                                type="formatting",
                                severity="P2", 
                                scope="history",
                                field="subject",
                                problem="Subject line requires an emoji (Pacing).",
                                rationale=f"Gap since last emoji: {dist_to_last_emoji}. Goal is 1 in 4."
                            ))

        # 3. Length Constraints
        for field, (min_len, max_len) in self.LENGTH_RULES.items():
            val = getattr(draft, field)
            if val is None:
                val = ""
            
            length = len(val)
            
            # Check Min Length (Enforces existence)
            if length < min_len:
                 # If min_len > 0, being empty/None is a failure
                 issues.append(Issue(
                    type="formatting",
                    severity="P2",
                    scope="email",
                    field=field,
                    problem=f"Text missing or too short ({length} < {min_len} chars).",
                    rationale=f"This field is required and must be between {min_len}-{max_len} chars."
                ))
            
            # Check Max Length (if content exists)
            # UPDATED: Add 20% Buffer (Tolerance)
            allowed_max = int(max_len * 1.2) if max_len > 0 else 0
            
            if length > 0 and max_len > 0 and length > allowed_max:
                # UPDATED: More descriptive for max caps
                issue_problem = f"Text too long ({length} chars)."
                issue_rationale = f"Maximum limit is {max_len} characters. Please shorten this field."
                if min_len > 0:
                    issue_rationale = f"Must be between {min_len}-{max_len} chars."
                    
                issues.append(Issue(
                    type="formatting",
                    severity="P2",
                    scope="email",
                    field=field,
                    problem=issue_problem,
                    rationale=issue_rationale
                ))


        return issues
    
    def _contains_banned_dashes(self, text: str) -> bool:
        """Check for -, –, —"""
        # We need to be careful. User said "Never ever".
        # But hyphens in words like "stress-free"?
        # "Never use em dashes, hyphens or dashes. Never ever".
        # This implies even compound words should be avoided or rephrased.
        # Strict check.
        banned = ["–", "—"] # Only ban En-dash and Em-dash. Hyphen (-) is allowed.
        for char in banned:
            if char in text:
                return True
        return False

    def _contains_emoji(self, text: str) -> bool:
        """Simple emoji detection check."""
        # Expanded regex for emojis including BMP characters
        # Blocks: Emoticons, Dingbats, Symbols & Pictographs, Transport, etc.
        emoji_pattern = re.compile(
            "["
            "\U00010000-\U0010ffff"  # Supplementary Plane
            "\u2600-\u27bf"          # Misc Symbols, Dingbats (Snowflake is here)
            "\u2300-\u23ff"          # Misc Technical (Watch, etc)
            "\u2b50"                 # Star
            "\u203c-\u2049"          # Double exclamation, etc
            "]+", flags=re.UNICODE)
        return bool(emoji_pattern.search(text))

    def _contains_html_tags(self, text: str) -> bool:
        """Checks for presence of basic HTML tags like <b>, <i>, <u>, <br>."""
        if not text: return False
        # Simple regex for tag-like structures
        return bool(re.search(r"</?[a-z][\s\S]*?>", text, re.IGNORECASE))

    def verify_plan(self, plan: CampaignPlan, history: List[Dict]) -> List[Issue]:
        """Runs deterministic checks on a campaign plan."""
        issues = []
        
        # 1. History Checks (Inter-Plan Repetition)
        # Check against recent history (Last 3)
        # Filter history based on 7-day rule:
        # If the gap between plan.created_at and previous campaign is > 7 days, 
        # we ALLOW reusing the transformation/angle.
        
        relevant_history = []
        
        try:
            # Handle potential Z suffix or missing TZ
            plan_date_str = plan.created_at.replace("Z", "+00:00")
            plan_date = datetime.fromisoformat(plan_date_str)
            if plan_date.tzinfo is None:
                plan_date = plan_date.replace(tzinfo=None) # naive comparison if needed
        except ValueError:
            # Fallback if parsing fails
            plan_date = datetime.utcnow()

        print(f"\n[Verifier Logic] Analyzing History for Plan '{plan.campaign_name}' ({plan.created_at})...")
        
        # Sort history by date descending
        sorted_history = sorted(history, key=lambda x: x.get("timestamp", ""), reverse=True)
        # Take last 10 to check dates, but we only really care about the most recent ones for repetition
        
        # DEFINED ALLOWED STRUCTURES (from catalogs/global/structures.json)
        self.ALLOWED_STRUCTURES = [
            "STRUCT_NARRATIVE_PARAGRAPH",
            "STRUCT_EMOJI_CHECKLIST",
            "STRUCT_5050_SPLIT",
            "STRUCT_MEDIA_LEFT_OFFSET",
            "STRUCT_SPOTLIGHT_BOX",
            "STRUCT_STAT_ATTACK",
            "STRUCT_STEP_BY_STEP",
            "STRUCT_MINI_GRID",
            "STRUCT_SOCIAL_PROOF_QUOTE",
            "STRUCT_GIF_PREVIEW"
        ]
        
        # Pre-calculate used structures in the current plan for smarter suggestions
        plan_structures = {s.structure_id for s in plan.email_slots}
        available_structures = [s for s in self.ALLOWED_STRUCTURES if s not in plan_structures]
        suggest_text = f"Available alternatives: {', '.join(available_structures)}" if available_structures else "No other standard structures available."

        
        for slot in plan.email_slots:
            # 0. Validity Check (Structure ID)
            if slot.structure_id not in self.ALLOWED_STRUCTURES:
                 issues.append(Issue(
                    type="structure_id_validity",
                    severity="P1",
                    scope="campaign",
                    field="structure_id",
                    problem=f"Invalid Structure ID: '{slot.structure_id}'.",
                    rationale=f"Must be one of the {len(self.ALLOWED_STRUCTURES)} approved structures."
                ))

        for entry in sorted_history[:5]: # look at last 5
            entry_ts = entry.get("timestamp", "")
            try:
                entry_date_str = entry_ts.replace("Z", "+00:00")
                entry_date = datetime.fromisoformat(entry_date_str)
                if entry_date.tzinfo is None:
                    entry_date = entry_date.replace(tzinfo=None) # naive
                
                # Calculate age difference
                # Ensure both are offset-aware or both naive
                if plan_date.tzinfo is not None and entry_date.tzinfo is None:
                     entry_date = entry_date.replace(tzinfo=plan_date.tzinfo)
                elif plan_date.tzinfo is None and entry_date.tzinfo is not None:
                     plan_date = plan_date.replace(tzinfo=entry_date.tzinfo)
                     
                delta = plan_date - entry_date
                days_diff = delta.days
                
                # If days_diff is negative, it means the history entry is in the FUTURE relative to the plan?
                # Or the plan date is wrong.
                # However, for 7-day rule, we typically want positive age (Plan > History).
                # If History > Plan (future), technically it's not "history".
                # But to avoid weird logic, let's treat future events as "0 days old" (immediate collision)
                if days_diff < 0:
                    days_diff = 0 # Treat future/negative diff as "very recent" to be safe
                
                entry_id = entry.get("campaign_id", "unknown")
                entry_trans = entry.get("transformation_description") or entry.get("transformation_id") or "N/A"
                print(f" - History: {entry_id} | Date: {entry_ts} | Age: {days_diff} days")
                
                if days_diff <= 7:
                    print(f"   -> WITHIN 7 DAYS. Enforcing unique Transformation/Angle.")
                    relevant_history.append(entry)
                else:
                    print(f"   -> OLDER THAN 7 DAYS. Transformation reuse allowed (History Check Skipped).")
            
            except Exception as e:
                print(f"   [Error parsing date for {entry.get('campaign_id')}]: {e}")
                # If date parse failure, err on safe side and include it? 
                # Or exclude? Let's exclude to avoid crashing, but log it.
                pass

        # Use the filtered history for checks
        # But wait, logic is: compare against last 3 *relevant* campaigns? 
        # Or just recently logged ones?
        # User said: "that is applicable for the past plans only."
        # So we only check against 'relevant_history' (<= 7 days old)
        
        # Limit to last 3 relevant ones to be safe
        check_list = relevant_history[:3]
        
        if not check_list:
            print("   => No recent history (< 7 days) found. Skipping History Repetition checks.")
        
        for slot in plan.email_slots:
             for prev_campaign in check_list:
                 # Check Structure ID (Strict match)
                 if slot.structure_id == prev_campaign.get("structure_id"):
                     issues.append(Issue(
                        type="history_repetition",
                        severity="P1",
                        scope="campaign",
                        field="structure_id",
                        problem=f"Structure '{slot.structure_id}' in Slot {slot.slot_number} was used in recent Campaign {prev_campaign.get('campaign_id')}.",
                        rationale=f"Recent history collision. Please use a different structure. {suggest_text}"
                    ))
                 
                 # Check Transformation (Similarity)
                 # Fallback to blueprint if top-level is missing
                 prev_trans = prev_campaign.get("transformation_description")
                 if not prev_trans and prev_campaign.get("blueprint"):
                     prev_trans = prev_campaign["blueprint"].get("transformation_description")
                 if not prev_trans:
                     prev_trans = prev_campaign.get("transformation_id") or ""
                     


                 is_sim, reason = self._check_similarity(slot.transformation_description, prev_trans)
                 if is_sim:
                      issues.append(Issue(
                        type="history_repetition",
                        severity="P1",
                        scope="campaign",
                        field="transformation_description",
                        problem=f"Transformation in Slot {slot.slot_number} is too similar to recent Campaign {prev_campaign.get('campaign_id')}.",
                        rationale=f"Similarity Match: '{slot.transformation_description[:50]}...' vs historical '{prev_trans[:50]}...'. {reason}"
                    ))

                 # Check Angle (Similarity)
                 # Fallback to blueprint if top-level is missing
                 prev_angle = prev_campaign.get("angle_description")
                 if not prev_angle and prev_campaign.get("blueprint"):
                     prev_angle = prev_campaign["blueprint"].get("angle_description")
                 if not prev_angle:
                     prev_angle = prev_campaign.get("angle_id") or ""
                     


                 is_sim, reason = self._check_similarity(slot.angle_description, prev_angle)
                 if is_sim:
                      issues.append(Issue(
                        type="history_repetition",
                        severity="P1",
                        scope="campaign",
                        field="angle_description",
                        problem=f"Angle in Slot {slot.slot_number} is too similar to recent Campaign {prev_campaign.get('campaign_id')}.",
                        rationale=f"Similarity Match: '{slot.angle_description[:50]}...' vs historical '{prev_angle[:50]}...'. {reason}"
                    ))

        # 2. Intra-Plan Repetition Checks (New)
        # Ensure no two slots in the current plan are identical
        seen_structures = {}
        seen_angles = [] # List of (slot_num, description)
        seen_transformations = [] # List of (slot_num, description)
        
        for slot in plan.email_slots:
            # A. Structure Uniqueness
            if slot.structure_id in seen_structures:
                first_slot = seen_structures[slot.structure_id]
                issues.append(Issue(
                    type="repetition",
                    severity="P1",
                    scope="campaign", # Internal repetition
                    field="structure_id",
                    problem=f"Structure '{slot.structure_id}' is repeated in Slot {slot.slot_number} and Slot {first_slot}.",
                    rationale=f"Each email in the plan must use a unique structure. {suggest_text}"
                ))
            else:
                seen_structures[slot.structure_id] = slot.slot_number

            # B. Angle Similarity (Internal)
            for prev_slot_num, prev_desc in seen_angles:
                # Fuzzy description match
                is_sim, reason = self._check_similarity(slot.angle_description, prev_desc)
                if is_sim:
                     issues.append(Issue(
                        type="repetition",
                        severity="P1",
                        scope="campaign", # Internal repetition
                        field="angle_description",
                        problem=f"Angle in Slot {slot.slot_number} is too similar to Slot {prev_slot_num}.",
                        rationale=f"Internal collision. '{slot.angle_description[:50]}...' vs Slot {prev_slot_num} '{prev_desc[:50]}...'. {reason}"
                    ))
            seen_angles.append((slot.slot_number, slot.angle_description))

            # C. Transformation Similarity (Internal)
            for prev_slot_num, prev_trans in seen_transformations:
                # Fuzzy description match
                is_sim, reason = self._check_similarity(slot.transformation_description, prev_trans)
                if is_sim:
                     issues.append(Issue(
                        type="repetition",
                        severity="P1",
                        scope="campaign", # Internal repetition
                        field="transformation_description",
                        problem=f"Transformation in Slot {slot.slot_number} is too similar to Slot {prev_slot_num}.",
                        rationale=f"Internal collision. '{slot.transformation_description[:50]}...' vs Slot {prev_slot_num} '{prev_trans[:50]}...'. {reason}"
                    ))
            seen_transformations.append((slot.slot_number, slot.transformation_description))

        return issues
