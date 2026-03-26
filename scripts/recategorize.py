#!/usr/bin/env python3
"""
Recategorize Trunk Press articles that are clearly miscategorized.
Uses keyword matching against title + tags to detect mismatches.
"""

import json
import glob
import os
from collections import Counter
from datetime import datetime

CATEGORIES = ['us', 'world', 'politics', 'business', 'health', 
              'entertainment', 'travel', 'sports', 'science', 'climate', 'tech']

# Keywords that strongly indicate a category
CATEGORY_SIGNALS = {
    'sports': [
        'football', 'soccer', 'cricket', 'tennis', 'nba', 'nfl', 'mlb', 'rugby',
        'boxing', 'mma', 'olympic', 'athlete', 'tournament', 'championship', 'league',
        'match', 'player', 'team', 'coach', 'goal', 'score', 'cup', 'medal',
        'cycling', 'marathon', 'salah', 'liverpool', 'fifa', 'premier league',
        'champions league', 'world cup', 'transfer', 'roster', 'playoff',
        'batting', 'pitcher', 'quarterback', 'touchdown', 'grand slam',
        'f1', 'formula 1', 'motorsport', 'ufc', 'wrestling', 'stadium'
    ],
    'tech': [
        'ai ', 'artificial intelligence', 'software', 'app ', 'cyber', 'technology',
        'computer', 'digital', 'internet', 'crypto', 'blockchain', 'robot',
        'algorithm', 'data breach', 'cloud computing', 'meta ', 'google', 'apple ',
        'microsoft', 'startup', 'silicon valley', 'chip', 'semiconductor',
        'tiktok', 'social media ban', 'hack', 'coding', 'video game', 'gaming',
        'machine learning', 'chatbot', 'openai', 'nvidia', 'android', 'ios',
        'browser', 'malware', 'ransomware', 'deepfake', 'quantum comput'
    ],
    'health': [
        'nhs', 'hospital', 'doctor', 'patient', 'medical', 'disease', 'cancer',
        'mental health', 'depression', 'vaccine', 'pandemic', 'surgery', 'diagnosis',
        'treatment', 'symptom', 'wellness', 'pharmaceutical', 'drug trial',
        'clinical trial', 'nurse', 'healthcare', 'sleep', 'diet', 'nutrition',
        'endometriosis', 'fertility', 'pregnancy', 'meningitis', 'stroke',
        'heart attack', 'diabetes', 'obesity', 'therapy'
    ],
    'climate': [
        'climate change', 'global warming', 'carbon emission', 'renewable energy',
        'solar panel', 'wind farm', 'deforestation', 'glacier', 'sea level',
        'el niño', 'la niña', 'wildfire', 'drought', 'flood', 'hurricane',
        'typhoon', 'tornado', 'unseasonal storm', 'extreme weather', 'pine marten',
        'endangered species', 'conservation', 'biodiversity', 'coral reef',
        'electric vehicle', 'ev ', 'net zero', 'paris agreement'
    ],
    'travel': [
        'tourist', 'tourism', 'travel ban', 'visa', 'airport', 'airline',
        'hotel', 'destination', 'vacation', 'holiday', 'coastal path',
        'great wall', 'heritage site', 'backpack', 'nomad', 'resort'
    ],
    'entertainment': [
        'movie', 'film', 'actor', 'actress', 'oscar', 'grammy', 'emmy',
        'netflix', 'disney', 'concert', 'album', 'music', 'celebrity',
        'hollywood', 'bollywood', 'box office', 'streaming', 'tv show',
        'comedian', 'dating show', 'reality tv', 'cosby', 'reacher'
    ],
    'science': [
        'scientist', 'research', 'study reveals', 'discovery', 'space',
        'nasa', 'satellite', 'quantum', 'physics', 'biology', 'chemistry',
        'laboratory', 'experiment', 'genome', 'dna', 'fossil', 'archaeology',
        'telescope', 'mars', 'asteroid', 'evolution', 'lab-grown',
        'transplant', 'breakthrough', 'starlink'
    ],
    'business': [
        'stock', 'market', 'economy', 'inflation', 'gdp', 'trade deal',
        'investment', 'revenue', 'profit', 'earnings', 'ipo', 'merger',
        'acquisition', 'bankruptcy', 'unemployment', 'interest rate',
        'central bank', 'wall street', 'ftse', 'nasdaq', 'oil price',
        'energy bill', 'fuel price', 'mortgage', 'housing market',
        'supply chain', 'manufacturing', 'retail', 'consumer spending'
    ],
    'politics': [
        'trump', 'biden', 'congress', 'senate', 'parliament', 'election',
        'vote', 'democrat', 'republican', 'labour', 'conservative', 'coalition',
        'referendum', 'legislation', 'sanction', 'diplomat', 'nato', 'un ',
        'united nations', 'foreign minister', 'prime minister', 'president',
        'governor', 'policy', 'geopolitic', 'ceasefire', 'peace deal',
        'nuclear deal', 'reparation'
    ],
    'us': [
        'us military', 'american', 'united states', 'dhs', 'ice agent',
        'border patrol', 'homeland security', 'pentagon', 'fbi', 'cia',
        'us deploy', 'us strike', 'us base'
    ],
    'world': [
        'humanitarian', 'refugee', 'civilian', 'human rights', 'protest',
        'demonstration', 'massacre', 'genocide', 'famine', 'crisis',
        'earthquake', 'tsunami', 'plane crash', 'crash kills',
        'church of england', 'britain', 'british', 'england', 'wales',
        'scotland', 'northern ireland', 'australia', 'new zealand',
        'indonesia', 'india ', 'pakistan', 'africa', 'kenya', 'nigeria',
        'south korea', 'japan ', 'germany', 'france ', 'italy ',
        'spain ', 'sweden', 'denmark', 'norway', 'netherlands'
    ]
}

def score_category(title, tags):
    """Score each category based on keyword matches in title + tags."""
    text = (title + ' ' + ' '.join(tags)).lower()
    scores = {}
    for cat, keywords in CATEGORY_SIGNALS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[cat] = score
    return scores

def best_category(title, tags, current_cat):
    """Return the best category, or current if uncertain."""
    scores = score_category(title, tags)
    if not scores:
        return current_cat
    
    # Only reclassify if the current category scores 0 AND another scores >= 2
    current_score = scores.get(current_cat, 0)
    best_cat = max(scores, key=scores.get)
    best_score = scores[best_cat]
    
    if current_score == 0 and best_score >= 2:
        return best_cat
    
    return current_cat

def main():
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src', 'data', 'trunkpress')
    fixes = []
    
    for f in sorted(glob.glob(os.path.join(data_dir, '*.json'))):
        if '_schema' in f:
            continue
        try:
            d = json.load(open(f))
            old_cat = d.get('category', '?')
            title = d.get('title', '')
            tags = d.get('tags', [])
            
            new_cat = best_category(title, tags, old_cat)
            
            if new_cat != old_cat:
                d['category'] = new_cat
                json.dump(d, open(f, 'w'), indent=2)
                fixes.append((old_cat, new_cat, title[:70]))
        except Exception as e:
            pass
    
    if fixes:
        print(f"[{datetime.now().isoformat()}] Recategorized {len(fixes)} articles:")
        for old, new, title in fixes:
            print(f"  {old:12} → {new:12} | {title}")
    else:
        print(f"[{datetime.now().isoformat()}] All articles correctly categorized.")
    
    # Print tally
    counts = Counter()
    for f in glob.glob(os.path.join(data_dir, '*.json')):
        if '_schema' in f:
            continue
        try:
            d = json.load(open(f))
            counts[d.get('category', '?')] += 1
        except:
            pass
    
    print(f"\nTally ({sum(counts.values())} total):")
    for cat, n in counts.most_common():
        print(f"  {cat}: {n}")

if __name__ == '__main__':
    main()
