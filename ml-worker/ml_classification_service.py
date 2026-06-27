"""
ML Classification Service for Transaction Categorization
Implements sentence transformers with few-shot learning and ONNX optimization
"""

import os
import json
import pickle
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import onnx
import onnxruntime as ort
import torch

# Configure structured logging via shared config (ML-LOG-001).
try:
    from app.logging_config import configure_logging  # type: ignore
except Exception:  # pragma: no cover
    try:
        from logging_config import configure_logging  # type: ignore
    except Exception:
        def configure_logging(_name: str) -> None:  # type: ignore
            return None
configure_logging("ml-worker")
logger = logging.getLogger(__name__)


# ML-PR-002: confidence-bucket spec. Section F (F-ml-worker-revival.md) defines
# four buckets so downstream gating (TransactionService ML_CONFIDENCE_THRESHOLD)
# can distinguish "no signal" from "weak signal". Mirrors but extends the
# 3-bucket helper in ml-worker/tests/helpers/confidence.py.
_CONF_HIGH = 0.85
_CONF_MEDIUM = 0.65
_CONF_LOW = 0.45


def _confidence_bucket(similarity: float) -> str:
    """Map cosine similarity to {high, medium, low, very_low}.

    NaN inputs raise ValueError to fail loudly on degenerate prototypes.
    """
    if similarity != similarity:  # NaN
        raise ValueError("similarity is NaN")
    if similarity >= _CONF_HIGH:
        return "high"
    if similarity >= _CONF_MEDIUM:
        return "medium"
    if similarity >= _CONF_LOW:
        return "low"
    return "very_low"


class TransactionClassifier:
    """
    Intelligent transaction categorization using sentence transformers
    with few-shot learning capabilities
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.sentence_model = None
        self.category_prototypes = {}
        self.scaler = StandardScaler()
        self.onnx_session = None
        self.model_version = "v1.0"
        
        # Categories with example transactions for few-shot learning (expanded for better accuracy)
        self.default_categories = {
            "Food & Dining": [
                "food purchase grocery store",
                "food purchase restaurant meal",
                "food purchase coffee shop",
                "food purchase fast food",
                "food purchase takeout order",
                "food purchase pizza delivery",
                "food purchase lunch combo",
                "food purchase dinner bill",
                "food purchase breakfast meal",
                "food purchase snack purchase",
                "grocery shopping weekly food",
                "grocery shopping produce section",
                "grocery shopping meat department",
                "grocery shopping dairy products",
                "grocery shopping frozen foods",
                "grocery shopping organic produce",
                "grocery shopping bulk items",
                "grocery shopping beverages drinks",
                "grocery shopping bakery bread",
                "grocery shopping deli counter",
                "restaurant dining italian food",
                "restaurant dining chinese takeout",
                "restaurant dining mexican cuisine",
                "restaurant dining american diner",
                "restaurant dining seafood dinner",
                "restaurant dining steakhouse meal",
                "restaurant dining family restaurant",
                "restaurant dining fine dining",
                "restaurant dining casual dining",
                "restaurant dining fast casual",
                "coffee shop latte purchase",
                "coffee shop espresso drink",
                "coffee shop pastry snack",
                "coffee shop iced coffee",
                "coffee shop breakfast sandwich",
                "coffee shop smoothie drink",
                "coffee shop tea beverage",
                "coffee shop muffin pastry",
                "coffee shop bagel breakfast",
                "coffee shop cappuccino drink",
                "food delivery meal order",
                "food delivery pizza order",
                "food delivery chinese food",
                "food delivery thai cuisine",
                "food delivery indian meal",
                "food delivery sushi order",
                "food delivery italian food",
                "food delivery mexican food",
                "food delivery burger meal",
                "food delivery sandwich order",
                "meal kit subscription box",
                "meal kit recipe ingredients",
                "meal kit cooking supplies",
                "meal kit organic meals",
                "meal kit vegetarian option",
                "meal kit family meals",
                "meal kit quick prep",
                "meal kit gourmet cooking",
                "meal kit healthy options",
                "meal kit weekly delivery",
                "bakery fresh bread purchase",
                "bakery pastry selection",
                "bakery cake custom order",
                "bakery cookie assortment",
                "bakery croissant breakfast",
                "bakery donut morning treat",
                "bakery muffin snack",
                "bakery pie dessert",
                "bakery specialty items",
                "bakery wedding cake order",
                "farmers market fresh produce",
                "farmers market organic vegetables",
                "farmers market local honey",
                "farmers market artisan bread",
                "farmers market seasonal fruit",
                "farmers market meat vendor",
                "farmers market cheese selection",
                "farmers market flower purchase",
                "farmers market prepared foods",
                "farmers market weekly shopping"
            ],
            "Transportation": [
                "transportation fuel gas station",
                "transportation fuel gasoline purchase",
                "transportation fuel diesel fuel",
                "transportation fuel fill up",
                "transportation fuel premium gas",
                "transportation fuel regular unleaded",
                "transportation fuel car refuel",
                "transportation fuel tank fill",
                "transportation fuel service station",
                "transportation fuel highway stop",
                "transportation rideshare uber ride",
                "transportation rideshare lyft ride",
                "transportation rideshare taxi fare",
                "transportation rideshare cab service",
                "transportation rideshare ride booking",
                "transportation rideshare app payment",
                "transportation rideshare city trip",
                "transportation rideshare airport ride",
                "transportation rideshare shared ride",
                "transportation rideshare premium car",
                "transportation public transit pass",
                "transportation public transit fare",
                "transportation public transit ticket",
                "transportation public transit bus pass",
                "transportation public transit metro card",
                "transportation public transit train ticket",
                "transportation public transit subway fare",
                "transportation public transit monthly pass",
                "transportation public transit weekly pass",
                "transportation public transit day pass",
                "transportation parking garage fee",
                "transportation parking meter payment",
                "transportation parking spot rental",
                "transportation parking downtown fee",
                "transportation parking airport fee",
                "transportation parking valet service",
                "transportation parking monthly pass",
                "transportation parking daily rate",
                "transportation parking validation fee",
                "transportation parking street meter",
                "transportation airline flight ticket",
                "transportation airline domestic flight",
                "transportation airline international flight",
                "transportation airline economy seat",
                "transportation airline business class",
                "transportation airline checked bag",
                "transportation airline seat upgrade",
                "transportation airline booking fee",
                "transportation airline travel insurance",
                "transportation airline change fee",
                "transportation car maintenance oil change",
                "transportation car maintenance brake service",
                "transportation car maintenance tire rotation",
                "transportation car maintenance auto repair",
                "transportation car maintenance tune up",
                "transportation car maintenance inspection fee",
                "transportation car maintenance battery replacement",
                "transportation car maintenance transmission service",
                "transportation car maintenance engine repair",
                "transportation car maintenance scheduled maintenance",
                "transportation car wash service",
                "transportation car wash exterior wash",
                "transportation car wash interior cleaning",
                "transportation car wash detailing service",
                "transportation car wash automatic wash",
                "transportation car wash hand wash",
                "transportation car wash vacuum service",
                "transportation car wash wax application",
                "transportation car wash premium service",
                "transportation car wash monthly membership",
                "transportation car rental daily rate",
                "transportation car rental weekend rental",
                "transportation car rental weekly rate",
                "transportation car rental insurance coverage",
                "transportation car rental economy car",
                "transportation car rental premium vehicle",
                "transportation car rental pickup truck",
                "transportation car rental luxury car",
                "transportation car rental compact car",
                "transportation car rental fuel charge"
            ],
            "Shopping": [
                "retail shopping online purchase",
                "retail shopping store purchase",
                "retail shopping merchandise buy",
                "retail shopping item purchase",
                "retail shopping product order",
                "retail shopping goods purchase",
                "retail shopping consumer goods",
                "retail shopping shopping spree",
                "retail shopping mall purchase",
                "retail shopping store visit",
                "clothing purchase apparel shopping",
                "clothing purchase fashion items",
                "clothing purchase wardrobe update",
                "clothing purchase seasonal clothes",
                "clothing purchase work attire",
                "clothing purchase casual wear",
                "clothing purchase formal wear",
                "clothing purchase accessories purchase",
                "clothing purchase shoes purchase",
                "clothing purchase designer clothing",
                "electronics purchase gadget buy",
                "electronics purchase computer equipment",
                "electronics purchase mobile device",
                "electronics purchase home electronics",
                "electronics purchase tech gadget",
                "electronics purchase digital device",
                "electronics purchase consumer electronics",
                "electronics purchase appliance purchase",
                "electronics purchase audio equipment",
                "electronics purchase gaming console",
                "home goods purchase household items",
                "home goods purchase home decor",
                "home goods purchase furniture purchase",
                "home goods purchase kitchen supplies",
                "home goods purchase bathroom supplies",
                "home goods purchase bedding purchase",
                "home goods purchase storage solutions",
                "home goods purchase cleaning supplies",
                "home goods purchase home organization",
                "home goods purchase interior design",
                "sporting goods purchase athletic gear",
                "sporting goods purchase exercise equipment",
                "sporting goods purchase outdoor gear",
                "sporting goods purchase fitness equipment",
                "sporting goods purchase sports apparel",
                "sporting goods purchase athletic shoes",
                "sporting goods purchase recreation equipment",
                "sporting goods purchase camping gear",
                "sporting goods purchase workout clothes",
                "sporting goods purchase sports accessories",
                "department store purchase general merchandise",
                "department store purchase variety shopping",
                "department store purchase multiple items",
                "department store purchase seasonal shopping",
                "department store purchase gift purchase",
                "department store purchase family shopping",
                "department store purchase clearance items",
                "department store purchase sale items",
                "department store purchase discount shopping",
                "department store purchase bargain hunting",
                "specialty store purchase niche items",
                "specialty store purchase unique products",
                "specialty store purchase specialized goods",
                "specialty store purchase craft supplies",
                "specialty store purchase hobby items",
                "specialty store purchase collectibles purchase",
                "specialty store purchase artisan goods",
                "specialty store purchase handmade items",
                "specialty store purchase custom products",
                "specialty store purchase premium goods"
            ],
            "Bills & Utilities": [
                "electric bill monthly payment",
                "water utility service bill",
                "internet service provider charge",
                "mobile phone bill",
                "gas utility bill payment",
                "rent monthly payment",
                "trash collection fee",
                "cable tv subscription",
                "home insurance premium",
                "security system monitoring fee",
                "duke energy electric",
                "florida power and light",
                "georgia power company",
                "pacific gas electric",
                "southern california edison",
                "con edison new york",
                "commonwealth edison chicago",
                "detroit edison company",
                "american water works",
                "california water service",
                "aqua america utilities",
                "united water resources",
                "verizon wireless plan",
                "at&t mobile service",
                "t mobile unlimited",
                "sprint network coverage",
                "xfinity internet cable",
                "spectrum tv internet",
                "cox communications bundle",
                "optimum cable service",
                "directv satellite tv",
                "dish network programming",
                "sling tv streaming",
                "youtube tv subscription",
                "state farm insurance",
                "allstate auto home",
                "geico car insurance",
                "progressive coverage",
                "farmers insurance group",
                "liberty mutual protection",
                "usaa military members",
                "nationwide insurance",
                "american family insurance",
                "mercury insurance company",
                "adt security monitoring",
                "vivint smart home",
                "brinks home security",
                "ring doorbell service",
                "simplisafe diy system",
                "frontpoint home security",
                "alarm.com monitoring",
                "guardian protection services",
                "xfinity mobile wireless",
                "spectrum mobile service",
                "cricket wireless prepaid",
                "boost mobile unlimited",
                "metro by t mobile",
                "mint mobile online",
                "visible verizon network",
                "google fi international",
                "republic wireless wifi",
                "ting mobile smart rates",
                "consumer cellular seniors",
                "jitterbug smart3 seniors",
                "straight talk walmart",
                "tracfone wireless prepaid",
                "net10 wireless service",
                "total wireless coverage",
                "simple mobile plans",
                "lycamobile international",
                "ultra mobile unlimited",
                "red pocket mobile mvno",
                "pure talk usa plans",
                "hello mobile coverage",
                "comcast business internet",
                "charter spectrum business",
                "verizon fios business",
                "att business fiber",
                "centurylink business dsl",
                "frontier communications rural",
                "windstream kinetic fiber",
                "consolidated communications",
                "brightspeed internet service",
                "hawaiian telcom fiber",
                "alaska communications",
                "gci alaska broadband",
                "midco regional internet",
                "sparklight cable internet",
                "mediacom cable service",
                "wow wide open west",
                "rcn cable internet",
                "grande communications texas",
                "astound broadband cable",
                "metronet fiber internet",
                "allo fiber gigabit",
                "google fiber gigabit",
                "att u verse tv",
                "verizon fios tv"
            ],
            "Entertainment": [
                "movie theater tickets",
                "netflix subscription payment",
                "spotify music subscription",
                "concert venue tickets",
                "museum admission fee",
                "gaming subscription xbox live",
                "theme park tickets",
                "stadium sports event tickets",
                "hulu streaming service",
                "book store purchase",
                "amc movie theaters",
                "regal cinemas imax",
                "cinemark movie club",
                "fandango ticket fees",
                "atom tickets mobile",
                "disney plus streaming",
                "amazon prime video",
                "hbo max subscription",
                "paramount plus shows",
                "peacock premium content",
                "apple tv plus original",
                "discovery plus nature",
                "espn plus sports",
                "showtime premium cable",
                "starz movie network",
                "cinemax action films",
                "crunchyroll anime streaming",
                "funimation japanese content",
                "twitch prime gaming",
                "youtube premium ad free",
                "apple music family plan",
                "amazon music unlimited",
                "pandora plus radio",
                "tidal high quality",
                "deezer music streaming",
                "soundcloud go plus",
                "audible audiobook service",
                "kindle unlimited reading",
                "comixology dc marvel",
                "steam game platform",
                "epic games store",
                "playstation network plus",
                "nintendo switch online",
                "xbox game pass ultimate",
                "discord nitro premium",
                "ticketmaster concert fees",
                "stubhub resale tickets",
                "vivid seats sports",
                "seatgeek live events",
                "barnes noble bookstore",
                "half price books used",
                "powell's books portland",
                "strand bookstore nyc",
                "books a million regional",
                "borders books closing",
                "waterstones uk books",
                "foyles london bookstore",
                "blackwells academic books",
                "indie bookstore local",
                "used bookstore vintage",
                "comic book shop monthly",
                "forbidden planet comics",
                "diamond comic distributors",
                "local game store magic",
                "board game cafe night",
                "dave and busters arcade",
                "chuck e cheese family",
                "main event entertainment",
                "topgolf driving range",
                "bowling alley league night",
                "laser tag arena party",
                "escape room experience",
                "mini golf adventure",
                "go kart racing track",
                "trampoline park jump",
                "rock climbing gym day",
                "indoor skydiving experience",
                "virtual reality arcade",
                "karaoke bar private room",
                "comedy club show tickets",
                "improv theater donation",
                "local theater season",
                "broadway show tickets",
                "off broadway experimental",
                "music festival weekend",
                "outdoor concert series",
                "symphony orchestra season",
                "opera house subscription",
                "jazz club cover charge",
                "dive bar live music",
                "sports bar game night",
                "wine tasting flight",
                "brewery tour tasting",
                "distillery whiskey tour",
                "escape the room puzzle",
                "mystery dinner theater",
                "murder mystery party",
                "trivia night team entry"
            ],
            "Healthcare": [
                "doctor visit copay",
                "pharmacy prescription pickup",
                "dental cleaning appointment",
                "vision eye exam copay",
                "medical lab test fee",
                "urgent care visit",
                "therapy session payment",
                "health insurance premium",
                "chiropractor appointment",
                "vaccination clinic fee",
                "kaiser permanente hmo",
                "blue cross blue shield",
                "aetna health insurance",
                "cigna medical coverage",
                "humana medicare advantage",
                "united healthcare plan",
                "anthem blue cross",
                "molina healthcare medicaid",
                "cvs pharmacy prescription",
                "walgreens drug store",
                "rite aid medication",
                "costco pharmacy savings",
                "walmart pharmacy generic",
                "kroger pharmacy rewards",
                "publix pharmacy consultation",
                "target pharmacy clinic",
                "minute clinic cvs",
                "patient first urgent care",
                "medexpress walk in",
                "concentra occupational health",
                "labcorp blood test",
                "quest diagnostics lab",
                "any lab test now",
                "ulta lab tests",
                "planned parenthood clinic",
                "community health center",
                "federally qualified health",
                "medicare part d",
                "medicaid state program",
                "cobra continuation coverage",
                "flexible spending account",
                "health savings account",
                "dental insurance delta",
                "vision insurance vsp",
                "massage therapy session",
                "acupuncture treatment",
                "physical therapy rehab",
                "mental health counseling",
                "addiction recovery program",
                "weight loss clinic",
                "dermatology skin care",
                "cardiology heart specialist",
                "orthopedic bone doctor",
                "neurology brain specialist",
                "oncology cancer treatment",
                "endocrinology diabetes care",
                "gastroenterology stomach doctor",
                "pulmonology lung specialist",
                "rheumatology joint pain",
                "nephrology kidney specialist",
                "urology bladder specialist",
                "gynecology women's health",
                "obstetrics pregnancy care",
                "pediatric children's doctor",
                "geriatric elderly care",
                "psychiatry mental health",
                "psychology therapy session",
                "social worker counseling",
                "family therapy session",
                "couples counseling relationship",
                "addiction counseling recovery",
                "eating disorder treatment",
                "trauma therapy ptsd",
                "grief counseling support",
                "anger management class",
                "stress management workshop",
                "meditation class mindfulness",
                "yoga therapy healing",
                "acupuncture pain relief",
                "massage therapy relaxation",
                "chiropractic spine adjustment",
                "physical therapy rehabilitation",
                "occupational therapy skills",
                "speech therapy communication",
                "hearing aid audiologist",
                "vision therapy eye exercises",
                "contact lens fitting",
                "eyeglasses prescription update",
                "lasik eye surgery",
                "cataract surgery procedure",
                "dental implant surgery",
                "root canal endodontic",
                "teeth whitening cosmetic",
                "orthodontic braces adjustment",
                "invisalign clear aligners",
                "dental crown replacement",
                "wisdom teeth extraction",
                "periodontal gum treatment"
            ],
            "Income": [
                "income salary deposit",
                "income wages earned",
                "income paycheck received",
                "income employment income",
                "income work payment",
                "income job earnings",
                "income monthly salary",
                "income weekly wages",
                "income biweekly pay",
                "income direct deposit",
                "income freelance payment",
                "income contractor payment",
                "income consulting fee",
                "income project payment",
                "income service payment",
                "income work completed",
                "income invoice payment",
                "income client payment",
                "income business income",
                "income professional fee",
                "income investment dividend",
                "income stock dividend",
                "income capital gains",
                "income investment return",
                "income portfolio income",
                "income interest income",
                "income bond income",
                "income mutual fund",
                "income retirement income",
                "income pension payment",
                "income business revenue",
                "income sales revenue",
                "income commission earned",
                "income bonus payment",
                "income profit sharing",
                "income performance bonus",
                "income annual bonus",
                "income overtime pay",
                "income holiday pay",
                "income vacation pay",
                "income government benefits",
                "income social security",
                "income unemployment benefits",
                "income disability benefits",
                "income welfare payment",
                "income tax refund",
                "income insurance claim",
                "income settlement payment",
                "income legal settlement",
                "income gift money",
                "income monetary gift",
                "income cash gift",
                "income family support",
                "income financial gift",
                "income inheritance money",
                "income estate payment",
                "income trust payment",
                "income rental income",
                "income property income",
                "income lease payment",
                "income royalty income",
                "income licensing income",
                "income patent income",
                "income creative income",
                "income artistic income",
                "income media income",
                "income streaming income",
                "income content income",
                "income online income",
                "income digital income",
                "income platform income",
                "income marketplace income"
            ]
        }
        
        # Add specialized financial categories
        self.default_categories.update({
            "Business Expenses": [
                "office supplies purchase",
                "business cards printing",
                "marketing materials design",
                "website hosting service",
                "domain name registration",
                "business insurance premium",
                "professional liability insurance",
                "workers compensation premium",
                "business license renewal",
                "trademark registration fee",
                "patent application cost",
                "legal consultation fee",
                "accounting services monthly",
                "bookkeeping service cost",
                "tax preparation fee",
                "business audit cost",
                "consultant hourly rate",
                "freelancer project payment",
                "contractor service fee",
                "equipment lease payment",
                "office rent monthly",
                "coworking space membership",
                "business travel flight",
                "hotel business trip",
                "rental car business",
                "client dinner expense",
                "business conference ticket",
                "trade show booth",
                "networking event fee",
                "professional membership dues",
                "industry certification cost",
                "software subscription saas",
                "cloud storage business",
                "cybersecurity service cost",
                "backup service monthly",
                "voip phone service",
                "video conferencing pro",
                "project management tool",
                "crm software monthly",
                "email marketing platform",
                "social media management",
                "advertising facebook ads",
                "google ads campaign",
                "linkedin premium business",
                "indeed job posting",
                "recruiting service fee",
                "employee training cost",
                "team building event",
                "office furniture purchase",
                "computer equipment upgrade",
                "printer supplies toner"
            ],
            "Education": [
                "tuition payment semester",
                "student loan payment",
                "textbook purchase required",
                "school supplies notebook",
                "online course enrollment",
                "certification exam fee",
                "professional development workshop",
                "conference attendance fee",
                "library late fee",
                "parking permit campus",
                "coursera specialization certificate",
                "udemy course lifetime access",
                "linkedin learning subscription",
                "masterclass annual membership",
                "skillshare premium account",
                "pluralsight technology training",
                "khan academy donation",
                "ted ed premium content",
                "brilliant math science",
                "duolingo plus language",
                "rosetta stone software",
                "babbel language learning",
                "memrise premium vocabulary",
                "anki flashcard premium",
                "quizlet plus study tools",
                "chegg textbook rental",
                "cengage mindtap access",
                "pearson mylab subscription",
                "mcgraw hill connect",
                "wiley plus homework",
                "college board sat prep",
                "kaplan test prep course",
                "princeton review gmat",
                "manhattan prep lsat",
                "barbri bar exam",
                "cpa review course becker",
                "cfa institute materials",
                "frm exam registration",
                "pmp certification training",
                "cissp security certification",
                "aws cloud certification",
                "google cloud training",
                "microsoft azure exam",
                "cisco networking cert",
                "comptia it certification",
                "salesforce admin cert",
                "tableau data visualization",
                "power bi training course",
                "python programming bootcamp",
                "javascript developer course"
            ],
            "Personal Care": [
                "haircut salon appointment",
                "hair color highlights",
                "nail salon manicure",
                "pedicure spa treatment",
                "facial skincare treatment",
                "massage therapy session",
                "spa day relaxation",
                "waxing hair removal",
                "eyebrow threading shaping",
                "eyelash extension appointment",
                "makeup artist session",
                "personal trainer session",
                "gym membership monthly",
                "yoga class pass",
                "pilates studio session",
                "spin class package",
                "barre fitness class",
                "crossfit gym membership",
                "martial arts dojo",
                "dance lessons ballroom",
                "swimming pool membership",
                "tennis court rental",
                "golf course green fees",
                "ski lift ticket",
                "rock climbing gym",
                "personal stylist consultation",
                "wardrobe makeover service",
                "image consultant session",
                "life coach meeting",
                "career counseling session",
                "financial advisor fee",
                "therapy session mental health",
                "psychiatrist appointment medication",
                "dermatologist acne treatment",
                "cosmetic surgery consultation",
                "laser hair removal",
                "botox injection treatment",
                "teeth whitening dentist",
                "orthodontist braces payment",
                "contact lens eye exam",
                "prescription glasses frames",
                "hearing test audiologist",
                "physical therapy appointment",
                "chiropractic adjustment session",
                "acupuncture pain relief",
                "naturopathic doctor visit",
                "nutritionist meal planning",
                "dietitian weight loss",
                "personal chef service",
                "meal prep delivery"
            ],
            "Gifts & Donations": [
                "birthday gift purchase",
                "wedding gift registry",
                "baby shower present",
                "graduation gift card",
                "anniversary flowers delivery",
                "valentine's day jewelry",
                "christmas presents shopping",
                "hanukkah gift tradition",
                "mother's day spa gift",
                "father's day tools",
                "charitable donation receipt",
                "church tithe offering",
                "nonprofit organization donation",
                "political campaign contribution",
                "gofundme medical fund",
                "disaster relief donation",
                "animal shelter donation",
                "food bank contribution",
                "homeless shelter support",
                "scholarship fund donation",
                "public radio donation",
                "museum membership donation",
                "library friends donation",
                "school fundraiser support",
                "sports team sponsorship",
                "local charity walk",
                "united way workplace",
                "red cross blood drive",
                "salvation army donation",
                "goodwill clothing donation",
                "habitat for humanity",
                "doctors without borders",
                "world wildlife fund",
                "greenpeace environmental",
                "amnesty international human rights",
                "oxfam poverty relief",
                "unicef children's fund",
                "american cancer society",
                "heart association donation",
                "diabetes research foundation",
                "alzheimers association donation",
                "st jude children's hospital",
                "shriners hospital donation",
                "wounded warrior project",
                "veterans administration support",
                "local veterans organization",
                "homeless veterans support",
                "animal rescue donation",
                "spca animal welfare",
                "peta animal rights"
            ]
        })
                
    def _models_root(self) -> str:
        """Resolve models root directory across environments.
        Preference order: MODELS_DIR env -> /app/models -> /app/ml_models.
        """
        env_dir = os.getenv('MODELS_DIR')
        if env_dir and os.path.isdir(env_dir):
            return env_dir
        for path in ("/app/models", "/app/ml_models"):
            if os.path.isdir(path):
                return path
        return "/app/models"

    def load_model(self):
        """Load the sentence transformer model"""
        try:
            # Check if model exists locally first
            models_root = self._models_root()
            local_model_path = os.path.join(models_root, self.model_name)
            if os.path.exists(local_model_path):
                logger.info(f"Loading local sentence transformer model (CPU): {local_model_path}")
                self.sentence_model = SentenceTransformer(local_model_path, device='cpu', cache_folder=models_root)
                logger.info("Local model loaded successfully")
            else:
                logger.info(f"Loading sentence transformer model from hub (CPU): {self.model_name}")
                self.sentence_model = SentenceTransformer(self.model_name, device='cpu', cache_folder=models_root)
                logger.info("Hub model loaded successfully")
            # Ensure eval mode for inference
            try:
                self.sentence_model.eval()
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def initialize_category_prototypes(self, custom_categories: Optional[Dict[str, List[str]]] = None):
        """Initialize category prototypes using few-shot examples"""
        if not self.sentence_model:
            self.load_model()
            
        categories = custom_categories or self.default_categories
        
        logger.info("Initializing category prototypes...")
        for category, examples in categories.items():
            # Encode example transactions (single-threaded to avoid Celery fork issues)
            embeddings = self.sentence_model.encode(
                examples,
                convert_to_tensor=False,
                show_progress_bar=False
            )
            # Create prototype as mean embedding
            prototype = np.mean(embeddings, axis=0)
            self.category_prototypes[category] = {
                'prototype': prototype,
                'examples': examples,
                'embedding_dim': len(prototype)
            }
        
        logger.info(f"Initialized {len(self.category_prototypes)} category prototypes")
    
    def add_category_example(self, category: str, example: str, user_id: Optional[str] = None):
        """Add a new example to a category and update prototype"""
        if not self.sentence_model:
            self.load_model()
            
        if category not in self.category_prototypes:
            self.category_prototypes[category] = {
                'prototype': None,
                'examples': [],
                'embedding_dim': 384  # Default for MiniLM
            }
        
        # Add example
        self.category_prototypes[category]['examples'].append(example)
        
        # Recompute prototype
        examples = self.category_prototypes[category]['examples']
        embeddings = self.sentence_model.encode(
            examples,
            convert_to_tensor=False,
            show_progress_bar=False
        )
        prototype = np.mean(embeddings, axis=0)
        self.category_prototypes[category]['prototype'] = prototype
        
        logger.info(f"Added example to {category}: {example}")
    
    def classify_transaction(self, description: str, amount: float = None, 
                           merchant: str = None) -> Dict:
        """Classify a transaction using few-shot learning"""
        if not self.sentence_model or not self.category_prototypes:
            raise ValueError("Model not initialized. Call load_model() and initialize_category_prototypes() first.")
        
        # Prepare input text
        input_text = description
        if merchant:
            input_text = f"{merchant} {description}"
        
        # Encode transaction
        transaction_embedding = self.sentence_model.encode(
            [input_text],
            convert_to_tensor=False,
            show_progress_bar=False
        )[0]
        
        # Calculate similarities to all prototypes
        similarities = {}
        for category, data in self.category_prototypes.items():
            prototype = data['prototype']
            similarity = cosine_similarity([transaction_embedding], [prototype])[0][0]
            similarities[category] = similarity
        
        # Find best match
        best_category = max(similarities, key=similarities.get)
        confidence = similarities[best_category]

        # ML-PR-002: real confidence bucket from cosine similarity.
        # Spec mirrors ml-worker/tests/helpers/confidence.py extended
        # with the "very_low" floor required by Section F (audit deliverable).
        confidence_level = _confidence_bucket(float(confidence))

        return {
            'predicted_category': best_category,
            'confidence': float(confidence),
            'confidence_level': confidence_level,
            'all_similarities': {k: float(v) for k, v in similarities.items()},
            'model_version': self.model_version,
            'timestamp': datetime.now().isoformat()
        }
    
    def batch_classify(self, transactions: List[Dict]) -> List[Dict]:
        """Classify multiple transactions in batch using vectorized operations"""
        # Ensure model and prototypes are ready
        if not self.sentence_model:
            logger.warning("Model not loaded during batch_classify, reloading...")
            self.load_model()
        if not self.category_prototypes:
            logger.warning("Prototypes not loaded during batch_classify, initializing...")
            self.initialize_category_prototypes()
            
        if not transactions:
            return []

        # Prepare batch texts (merchant + description when available)
        texts: List[str] = []
        for t in transactions:
            desc = t.get('description', '') or ''
            merchant = t.get('merchant')
            texts.append(f"{merchant} {desc}".strip() if merchant else desc)

        # Encode all texts at once for efficiency
        embeddings = self.sentence_model.encode(
            texts,
            convert_to_tensor=False,
            show_progress_bar=False,
            batch_size=min(64, max(1, len(texts)))
        )
        # Normalize embeddings for cosine similarity
        emb_norms = np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-12
        norm_embeddings = embeddings / emb_norms

        # Stack category prototypes and normalize
        categories = list(self.category_prototypes.keys())
        protos = np.stack([self.category_prototypes[c]['prototype'] for c in categories], axis=0)
        proto_norms = np.linalg.norm(protos, axis=1, keepdims=True) + 1e-12
        norm_protos = protos / proto_norms

        # Compute cosine similarity matrix (N x C)
        sims = norm_embeddings @ norm_protos.T

        results: List[Dict] = []
        for i, t in enumerate(transactions):
            # Argmax over categories
            idx = int(np.argmax(sims[i]))
            best_category = categories[idx]
            confidence = float(sims[i, idx])

            # ML-PR-002: real confidence bucket from cosine similarity.
            confidence_level = _confidence_bucket(confidence)

            # Collect per-category similarities for optional UI
            all_similarities = {categories[j]: float(sims[i, j]) for j in range(len(categories))}

            results.append({
                'predicted_category': best_category,
                'confidence': confidence,
                'confidence_level': confidence_level,
                'all_similarities': all_similarities,
                'model_version': self.model_version,
                'timestamp': datetime.now().isoformat(),
                'transaction_id': t.get('id')
            })

        return results
    
    
    def export_to_onnx(self, output_path: str = "models/transaction_classifier.onnx"):
        """Export model to ONNX format for production deployment"""
        if not self.sentence_model:
            raise ValueError("Model not loaded")
        
        try:
            # Create dummy input for tracing
            dummy_input = torch.randn(1, 512)  # Max sequence length
            
            # Export the transformer model
            torch.onnx.export(
                self.sentence_model[0].auto_model,
                dummy_input,
                output_path,
                export_params=True,
                opset_version=11,
                do_constant_folding=True,
                input_names=['input'],
                output_names=['output'],
                dynamic_axes={
                    'input': {0: 'batch_size', 1: 'sequence'},
                    'output': {0: 'batch_size'}
                }
            )
            
            logger.info(f"Model exported to ONNX: {output_path}")
            
        except Exception as e:
            logger.error(f"ONNX export failed: {e}")
            # Fallback: save prototypes as numpy arrays
            self.save_prototypes(output_path.replace('.onnx', '_prototypes.pkl'))
    
    def quantize_model(self, model_path: str, quantized_path: str = None):
        """Apply INT8 quantization to ONNX model"""
        try:
            import onnxruntime.quantization as quantization
            
            if quantized_path is None:
                quantized_path = model_path.replace('.onnx', '_quantized.onnx')
            
            quantization.quantize_dynamic(
                model_path,
                quantized_path,
                weight_type=quantization.QuantType.QInt8
            )
            
            logger.info(f"Model quantized: {quantized_path}")
            return quantized_path
            
        except Exception as e:
            logger.error(f"Quantization failed: {e}")
            return model_path
    
    def load_onnx_model(self, model_path: str):
        """Load ONNX model for inference"""
        try:
            self.onnx_session = ort.InferenceSession(model_path)
            logger.info(f"ONNX model loaded: {model_path}")
        except Exception as e:
            logger.error(f"Failed to load ONNX model: {e}")
    
    def save_prototypes(self, filepath: str):
        """Save category prototypes for persistence.

        ML-SEC-001: switched away from `pickle` (RCE on load if the file is
        attacker-writable). We persist a `.safetensors` array file plus a
        sidecar JSON with the category-name → row-index mapping and metadata.
        Old `.pkl` paths are migrated transparently below in load_prototypes
        and via `ml-worker/scripts/migrate_pickles.py`.
        """
        # Normalise to .safetensors regardless of caller-supplied extension.
        base, _ = os.path.splitext(filepath)
        st_path = base + ".safetensors"
        meta_path = base + ".meta.json"
        os.makedirs(os.path.dirname(st_path) or ".", exist_ok=True)

        protos = self.category_prototypes or {}
        if not protos:
            logger.warning("save_prototypes: no prototypes to save")
            return

        try:
            from safetensors.numpy import save_file as _st_save
        except Exception as e:
            raise RuntimeError(
                "safetensors is required for prototype persistence (ML-SEC-001). "
                "Install with `pip install safetensors`."
            ) from e

        # safetensors expects a flat dict of name -> ndarray. Each prototype
        # is already an ndarray; just ensure dtype is consistent.
        tensors = {
            str(name): np.asarray(arr, dtype=np.float32)
            for name, arr in protos.items()
        }
        _st_save(tensors, st_path)

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "model_version": self.model_version,
                    "model_name": self.model_name,
                    "categories": list(tensors.keys()),
                    "format": "safetensors-v1",
                },
                f,
            )

        logger.info(f"Prototypes saved to {st_path} (+ {os.path.basename(meta_path)})")

    def load_prototypes(self, filepath: str):
        """Load category prototypes from disk.

        ML-SEC-001: prefer `.safetensors`. Fall back to legacy `.pkl` ONLY
        when explicitly opted in via `ALLOW_LEGACY_PICKLE_LOAD=1`, with a
        loud warning. The recommended migration path is
        `ml-worker/scripts/migrate_pickles.py`.
        """
        try:
            base, _ = os.path.splitext(filepath)
            st_path = base + ".safetensors"
            meta_path = base + ".meta.json"

            if os.path.exists(st_path):
                from safetensors.numpy import load_file as _st_load
                tensors = _st_load(st_path)
                self.category_prototypes = {k: v for k, v in tensors.items()}
                if os.path.exists(meta_path):
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    self.model_version = meta.get("model_version", self.model_version)
                logger.info(f"Prototypes loaded from {st_path}")
                return

            # Legacy pickle fallback — disabled by default.
            if os.path.exists(filepath) and filepath.endswith(".pkl"):
                if os.environ.get("ALLOW_LEGACY_PICKLE_LOAD") == "1":
                    logger.warning(
                        "Loading legacy pickle prototypes from %s — RCE risk. "
                        "Run ml-worker/scripts/migrate_pickles.py to convert.",
                        filepath,
                    )
                    with open(filepath, "rb") as f:
                        data = pickle.load(f)  # noqa: S301 — gated behind env flag
                    self.category_prototypes = data["prototypes"]
                    self.model_version = data.get("model_version", "v1.0")
                    return
                logger.error(
                    "Refusing to load legacy pickle prototypes at %s. "
                    "Set ALLOW_LEGACY_PICKLE_LOAD=1 only for a one-time migration.",
                    filepath,
                )
                return

            logger.info(f"Prototypes file not found at {filepath}; will continue with defaults")
        except Exception as e:
            logger.warning(f"Failed to load prototypes from {filepath}: {e}")
    
    def get_model_performance(self) -> Dict:
        """Calculate model performance metrics"""
        return {
            'total_predictions': 0,
            'total_feedback': 0,
            'correct_predictions': 0,
            'accuracy': 0.0,
            'model_version': self.model_version,
            'categories_count': len(self.category_prototypes),
            'users_with_feedback': 0
        }

# Global classifier instance
classifier = TransactionClassifier()
