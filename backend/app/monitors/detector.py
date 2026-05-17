"""Keyword matching engine with multiple strategies"""
import re
import logging
from dataclasses import dataclass
from typing import List, Dict, Any
from rapidfuzz import fuzz
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class Match:
    """Single match result"""
    keyword: str
    match_type: str
    start_index: int
    end_index: int
    context: str
    confidence: float


class MatchResult:
    """Aggregated match result with confidence scoring"""
    
    def __init__(self, matches: List[Match]):
        self.matches = matches
        self.matched_keywords = list(set(m.keyword for m in matches))
        self.match_types = list(set(m.match_type for m in matches))
        self.confidence_score = self._calculate_confidence()
    
    def _calculate_confidence(self) -> float:
        if not self.matches:
            return 0.0
        
        weights = {
            "exact": 1.0,
            "email_pattern": 1.0,
            "regex": 0.9,
            "fuzzy": 0.7,
            "domain_similarity": 0.8
        }
        
        weighted_sum = sum(
            m.confidence * weights.get(m.match_type, 0.5)
            for m in self.matches
        )
        
        normalized = weighted_sum / (1 + len(self.matches) * 0.1)
        
        return min(1.0, normalized)
    
    def is_match(self, threshold: float = 0.5) -> bool:
        return self.confidence_score >= threshold


class ExactMatcher:
    """Case-insensitive exact keyword matching"""
    
    def match(self, content: str, keywords: List[str]) -> List[Match]:
        matches = []
        content_lower = content.lower()
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            start = 0
            
            while True:
                index = content_lower.find(keyword_lower, start)
                if index == -1:
                    break
                
                context_start = max(0, index - 100)
                context_end = min(len(content), index + len(keyword) + 100)
                context = content[context_start:context_end]
                
                matches.append(Match(
                    keyword=keyword,
                    match_type="exact",
                    start_index=index,
                    end_index=index + len(keyword),
                    context=context,
                    confidence=1.0
                ))
                
                start = index + 1
        
        return matches
    
    def match_emails(self, content: str, patterns: List[str]) -> List[Match]:
        """Match email patterns like @company.com"""
        matches = []
        
        email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        
        for email_match in re.finditer(email_regex, content):
            email = email_match.group()
            
            for pattern in patterns:
                if pattern.lower() in email.lower():
                    matches.append(Match(
                        keyword=pattern,
                        match_type="email_pattern",
                        start_index=email_match.start(),
                        end_index=email_match.end(),
                        context=email,
                        confidence=1.0
                    ))
        
        return matches


class FuzzyMatcher:
    """Fuzzy matching for typosquatting detection using sliding window"""
    
    def __init__(self, threshold: int = 85):
        self.threshold = threshold
    
    def match(self, content: str, keywords: List[str]) -> List[Match]:
        matches = []
        content_lower = content.lower()
        content_len = len(content_lower)
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            kw_len = len(keyword_lower)
            
            if kw_len == 0 or content_len < kw_len:
                continue
            
            seen_positions = set()
            
            for i in range(content_len - kw_len + 1):
                window = content_lower[i:i + kw_len]
                ratio = fuzz.ratio(keyword_lower, window, score_cutoff=self.threshold)
                
                if self.threshold <= ratio < 100 and i not in seen_positions:
                    seen_positions.add(i)
                    
                    context_start = max(0, i - 50)
                    context_end = min(content_len, i + kw_len + 50)
                    context = content[context_start:context_end]
                    
                    matches.append(Match(
                        keyword=keyword,
                        match_type="fuzzy",
                        start_index=i,
                        end_index=i + kw_len,
                        context=context,
                        confidence=ratio / 100.0
                    ))
        
        return matches


class RegexMatcher:
    """Custom regex pattern matching"""
    
    def match(self, content: str, patterns: List[str]) -> List[Match]:
        matches = []
        
        for pattern_str in patterns:
            try:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                
                for match in pattern.finditer(content):
                    context_start = max(0, match.start() - 50)
                    context_end = min(len(content), match.end() + 50)
                    context = content[context_start:context_end]
                    
                    matches.append(Match(
                        keyword=pattern_str,
                        match_type="regex",
                        start_index=match.start(),
                        end_index=match.end(),
                        context=context,
                        confidence=0.9
                    ))
            except re.error:
                logger.warning(f"Invalid regex pattern skipped: {pattern_str}")
                continue
        
        return matches


class DomainSimilarityMatcher:
    """Detect similar domains (typosquatting, homograph attacks)"""
    
    def __init__(self, threshold: float = 0.8):
        self.threshold = threshold
    
    def match(self, content: str, target_domain: str) -> List[Match]:
        matches = []
        
        if not target_domain:
            return matches
        
        domain_regex = r'\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b'
        
        for match in re.finditer(domain_regex, content, re.IGNORECASE):
            found_domain = match.group()
            
            similarity = SequenceMatcher(
                None, 
                target_domain.lower(), 
                found_domain.lower()
            ).ratio()
            
            if similarity >= self.threshold and similarity < 1.0:
                context_start = max(0, match.start() - 50)
                context_end = min(len(content), match.end() + 50)
                context = content[context_start:context_end]
                
                matches.append(Match(
                    keyword=target_domain,
                    match_type="domain_similarity",
                    start_index=match.start(),
                    end_index=match.end(),
                    context=context,
                    confidence=similarity
                ))
        
        return matches


class KeywordMatcher:
    """
    Multi-strategy keyword matching engine with:
    1. Exact matching
    2. Fuzzy matching (Levenshtein distance)
    3. Regex pattern matching
    4. Domain similarity scoring
    """
    
    def __init__(self):
        self.exact_matcher = ExactMatcher()
        self.fuzzy_matcher = FuzzyMatcher(threshold=85)
        self.regex_matcher = RegexMatcher()
        self.domain_matcher = DomainSimilarityMatcher(threshold=0.8)
    
    def match(self, content: str, brand: Dict[str, Any]) -> MatchResult:
        """
        Apply all matching strategies and return combined results.
        """
        user_keywords = brand.get('keywords', []) or []
        brand_name = brand.get('name', '')
        domain = brand.get('domain', '')

        exact_keywords = list(user_keywords)
        if brand_name and brand_name not in exact_keywords:
            exact_keywords.append(brand_name)
        domain_root = domain.split('.')[0] if domain else ''
        if domain and domain not in exact_keywords:
            exact_keywords.append(domain)
        if domain_root and domain_root not in exact_keywords:
            exact_keywords.append(domain_root)

        fuzzy_keywords = list(user_keywords)
        if brand_name and brand_name not in fuzzy_keywords:
            fuzzy_keywords.append(brand_name)

        results = []
        results.extend(self.exact_matcher.match(content, exact_keywords))
        results.extend(self.exact_matcher.match_emails(content, brand.get('email_patterns', [])))
        results.extend(self.fuzzy_matcher.match(content, fuzzy_keywords))
        results.extend(self.regex_matcher.match(content, brand.get('regex_patterns', [])))
        results.extend(self.domain_matcher.match(content, domain))
        return MatchResult(results)
