"""Builds content/software-development.json, the seed learning path.

The structure (six chapters of five checkpoints, each a sequence of video / lesson / quiz / task parts)
follows the product design. Chapter 1 is fully written; later chapters are published as topics only.

    uv run python scripts/build_seed.py
"""

import json
import re
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "content" / "software-development.json"
MINUTES = {"Video": 2, "Lesson": 3, "Quiz": 2, "Task": 5}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower().replace("é", "e").replace("&", "and")).strip("-")


def parts(*items: tuple[str, str]) -> list[dict]:
    return [{"kind": kind, "title": title, "minutes": MINUTES[kind]} for kind, title in items]


def checkpoint(cid: str, title: str, summary: str, output: str, part_list: list[dict], content: dict | None = None) -> dict:
    lesson = {
        "id": cid,
        "title": title,
        "minutes": sum(p["minutes"] for p in part_list),
        "xp": 10 * len(part_list) + 10,
        "summary": summary,
        "parts": part_list,
        "output": output,
    }
    if content:
        lesson["content"] = content
    return lesson


def quiz_question(qid: str, prompt: str, options: list[str], correct: int, why: str) -> dict:
    ids = "abc"
    return {
        "id": qid,
        "prompt": prompt,
        "options": [{"id": ids[i], "label": label} for i, label in enumerate(options)],
        "correct_option_id": ids[correct],
        "explanation": why,
    }


# ---------------------------------------------------------------- Chapter 1: written in full

CP1 = checkpoint(
    "upload-your-resume",
    "Upload your résumé",
    "Upload your résumé in any form, in any language. We score it on six criteria and show what to fix first.",
    "A 0–100 score and a list of issues across the six criteria.",
    parts(("Video", "How a US client picks a freelancer"), ("Lesson", "What we check in your résumé"), ("Task", "Upload your résumé")),
    {
        "blocks": [
            {
                "type": "youtube", "key": "video", "title": "How a US client picks a freelancer", "video_id": "hl5uYGjiRYQ",
                "points": [
                    "A client scans dozens of profiles and spends a few seconds on each",
                    "They look for three things: a clear specialization, a proven result, clear English",
                    "The résumé is raw material: we build LinkedIn, Upwork and Fiverr from it",
                    "What you get by the end of the chapter: a strong résumé, a niche, an offer and three cases",
                ],
            },
            {
                "type": "markdown", "key": "criteria", "title": "What we check in your résumé",
                "body": "Upload it as it is today. We score six things and show what to fix first:\n\n1. **Language**: English, without word-for-word phrasing from another language\n2. **Length**: one page for up to 10 years of experience\n3. **Structure**: contacts, summary, experience (newest first), skills, education\n4. **Results**: numbers in the experience bullets\n5. **Relevance**: the experience fits remote work for a US client\n6. **Red flags**: photo, age, marital status, unexplained gaps",
            },
            {
                "type": "action_group", "key": "task", "title": "Upload your résumé",
                "intro": "A PDF file. Only its text is read; the file itself is not stored.",
                "action_keys": ["resume-check"],
            },
        ],
        "actions": [
            {"type": "document_review", "key": "resume-check", "title": "Your résumé", "capability": "resume_review",
             "asset_type": "resume_review", "submit_label": "Upload PDF"},
        ],
    },
)

CP2 = checkpoint(
    "fix-the-top-3-issues",
    "Fix the top 3 issues",
    "In the US a résumé is a short document about results, not a personal form. Personal details are left out so they give no grounds for hiring discrimination.",
    "A résumé that scores 70 or higher.",
    parts(("Video", "Résumé teardown: before and after"), ("Lesson", "Rules of a US résumé"), ("Lesson", "The strong bullet formula"),
          ("Quiz", "Check yourself"), ("Task", "Fix the three main issues")),
    {
        "blocks": [
            {"type": "youtube", "key": "video", "title": "Résumé teardown: before and after", "video_id": "s9UzlTfNdQo"},
            {
                "type": "markdown", "key": "rules", "title": "Rules of a US résumé",
                "body": "- **One page** for up to 10 years of experience\n- **No photo, age, date of birth or marital status**\n- **Newest job first**\n- **Results, not duties**\n- **Plain English**: short sentences, no translated idioms",
            },
            {
                "type": "markdown", "key": "bullet", "title": "The strong bullet formula",
                "body": "**Action verb + what you did + result with a number.**\n\nWeak: “Responsible for the orders API.”\n\nStrong: “Rebuilt the orders API, cutting response time from 900 ms to 200 ms.”\n\nNo exact number? Use an honest estimate and say so: “about 30% faster”.",
            },
            {"type": "quiz", "key": "check", "title": "Check yourself", "action_keys": ["resume-quiz"]},
            {
                "type": "action_group", "key": "task", "title": "Fix the three main issues",
                "intro": "Fix the top issues from your first check, then upload the new version. You need 70 or more.",
                "action_keys": ["resume-recheck"],
            },
        ],
        "actions": [
            {"type": "quiz", "key": "resume-quiz", "title": "Pick the better choice", "passing_score": 0.66, "questions": [
                quiz_question("q1", "Which bullet is stronger?",
                              ["Worked on the mobile app", "Cut app start time from 4 s to 1.5 s by lazy-loading screens", "Was part of a great mobile team"], 1,
                              "It starts with an action and ends with a measured result."),
                quiz_question("q2", "What should a US résumé leave out?",
                              ["Your photo and date of birth", "Your skills", "Your most recent job"], 0,
                              "Personal details are left out so they give no grounds for discrimination."),
                quiz_question("q3", "You have 6 years of experience. How long should the résumé be?",
                              ["As long as it takes", "Three pages, one per period", "One page"], 2,
                              "One page for up to 10 years. A client spends seconds on it."),
            ]},
            {"type": "document_review", "key": "resume-recheck", "title": "Your improved résumé", "capability": "resume_review",
             "min_score": 70, "asset_type": "resume_review", "submit_label": "Upload new version"},
        ],
    },
)

CP3 = checkpoint(
    "pick-a-niche",
    "Pick a niche",
    "Choose one way to narrow down. A good niche passes three checks: you have experience that proves it, there are jobs for it, and you can do the work on your own.",
    "A niche saved to your profile, backed by one experience bullet.",
    parts(("Video", "Why the generalist loses"), ("Lesson", "Three ways to narrow down"), ("Task", "Pick your niche")),
    {
        "blocks": [
            {"type": "youtube", "key": "video", "title": "Why the generalist loses", "video_id": "62Fg_3PS_dw"},
            {
                "type": "markdown", "key": "ways", "title": "Three ways to narrow down",
                "body": "Pick **one**:\n\n- **By industry**: “for e-commerce stores”\n- **By problem**: “slow apps”, “manual reporting”\n- **By technology**: “Shopify”, “React Native”\n\nA good niche passes three checks: your experience proves it, there are jobs for it, and you can do the work alone.",
            },
            {"type": "action_group", "key": "task", "title": "Pick your niche", "action_keys": ["niche-draft", "save-niche"]},
        ],
        "actions": [
            {"type": "text_submission", "key": "niche-draft", "title": "Your niche", "submit_label": "Save draft", "fields": [
                {"name": "niche", "label": "Your niche in one line", "min_length": 15, "max_length": 160, "examples": {
                    "default": "Internal tools for small logistics companies", "websites": "Fast marketing sites for local service businesses",
                    "web_apps": "Customer dashboards for B2B SaaS startups", "mobile_apps": "Booking apps for fitness studios",
                    "backend": "API integrations for e-commerce stores", "automation": "Reporting automation for small online shops"}},
                {"name": "proof", "label": "One experience bullet that proves it", "help": "Real work. Label practice projects as practice.",
                 "min_length": 20, "max_length": 300},
            ]},
            {"type": "save_asset", "key": "save-niche", "title": "Save your niche", "asset_type": "freelancer_niche", "source_action_key": "niche-draft"},
        ],
    },
)

CP4 = checkpoint(
    "one-line-offer",
    "One-line offer",
    "The offer becomes the headline on every profile. Formula: I help [who] [get a result] with [skill]. A client should know in one read whether you are for them.",
    "A one-line offer in English, up to 120 characters, saved to your profile.",
    parts(("Lesson", "The offer formula"), ("Quiz", "Find the weak spot"), ("Task", "Write your offer")),
    {
        "blocks": [
            {
                "type": "markdown", "key": "formula", "title": "The offer formula",
                "body": "**I help [who] [get a result] with [skill].**\n\n“I help online stores stop losing orders with fast, reliable checkout APIs.”\n\nAs a {{role}}, you fill three slots: the audience, the result, the skill. Up to 120 characters, in English.",
            },
            {"type": "quiz", "key": "check", "title": "Find the weak spot", "action_keys": ["offer-quiz"]},
            {"type": "action_group", "key": "task", "title": "Write your offer", "action_keys": ["offer-draft", "offer-feedback", "save-offer"]},
        ],
        "actions": [
            {"type": "quiz", "key": "offer-quiz", "title": "What is missing?", "passing_score": 0.66, "questions": [
                quiz_question("q1", "“I build great software with Python.” What is missing?",
                              ["The skill", "The audience and the result", "Nothing"], 1,
                              "It names a skill, but not who it is for or what they get."),
                quiz_question("q2", "“I help clinics.” What is missing?",
                              ["The result and the skill", "The audience", "Nothing"], 0,
                              "The audience is clear. The client still cannot tell what changes for them or how."),
                quiz_question("q3", "Which offer is complete?",
                              ["Full-stack developer, 5 years", "I help SaaS teams cut support tickets with clear customer dashboards", "I help everyone with anything"], 1,
                              "It names the audience, the result and the skill."),
            ]},
            {"type": "text_submission", "key": "offer-draft", "title": "Your one-line offer", "submit_label": "Save draft", "fields": [
                {"name": "offer", "label": "I help [who] [get a result] with [skill]", "help": "In English, up to 120 characters.",
                 "min_length": 30, "max_length": 120, "examples": {
                    "default": "I help small teams replace spreadsheets with simple internal tools",
                    "websites": "I help local service businesses get booked online with fast, simple websites",
                    "web_apps": "I help SaaS teams cut support tickets with clear customer dashboards",
                    "mobile_apps": "I help fitness studios fill classes with easy booking apps",
                    "backend": "I help online stores stop losing orders with fast, reliable checkout APIs",
                    "automation": "I help small shops get weekly numbers without manual work, with reporting automation"}},
            ]},
            {"type": "ai_review", "key": "offer-feedback", "title": "Coach feedback", "capability": "freelance_offer_feedback",
             "source_action_key": "offer-draft", "required": False, "instructions": "The coach reads your offer and suggests how to sharpen it."},
            {"type": "save_asset", "key": "save-offer", "title": "Save your offer", "asset_type": "freelancer_offer", "source_action_key": "offer-draft"},
        ],
    },
)

CASE_HELP = "Three or four sentences: the problem, what you did, the result with a number."
CP5 = checkpoint(
    "three-cases-with-numbers",
    "Three cases with numbers",
    "A case is three or four sentences: the problem in business terms, what you did, and a result with a number.",
    "Three cases saved to your profile, each with a problem, an action and a result.",
    parts(("Video", "How to tell a case without big-name clients"), ("Lesson", "The case formula"), ("Task", "Fill in three cases"), ("Lesson", "Chapter wrap-up")),
    {
        "blocks": [
            {"type": "youtube", "key": "video", "title": "How to tell a case without big-name clients", "video_id": "UrXIa816grU"},
            {
                "type": "markdown", "key": "formula", "title": "The case formula",
                "body": "1. **Problem** in business terms\n2. **What you did**\n3. **Result** with a number\n\nNo famous client needed. A job, a side project or a practice project all work, as long as a practice project is called practice.",
            },
            {"type": "action_group", "key": "task", "title": "Fill in three cases",
             "intro": "Cases that match your niche work best.", "action_keys": ["cases-draft", "save-cases"]},
            {
                "type": "markdown", "key": "wrap-up", "title": "Chapter wrap-up",
                "body": "You now have the raw material for every profile: a résumé that passes the check, a niche, a one-line offer and three cases.\n\nNext you turn them into a LinkedIn profile that says what you sell.",
            },
        ],
        "actions": [
            {"type": "text_submission", "key": "cases-draft", "title": "Your three cases", "submit_label": "Save draft", "fields": [
                {"name": f"case-{n}", "label": f"Case {n}", "help": CASE_HELP, "min_length": 80, "max_length": 600, "require_digit": True,
                 **({"examples": {"default": "A store lost orders at checkout. I rebuilt the payment step. Failed payments fell from 6% to 2%."}} if n == 1 else {})}
                for n in (1, 2, 3)
            ]},
            {"type": "save_asset", "key": "save-cases", "title": "Save your cases", "asset_type": "portfolio_cases", "source_action_key": "cases-draft"},
        ],
    },
)

# ---------------------------------------------------------------- Chapters 2-6: topics only

V, L, Q, T = "Video", "Lesson", "Quiz", "Task"
LATER = [
    ("LinkedIn", "blue", "A profile that says what you sell, built from your offer and cases.", "A LinkedIn profile that says what you sell", [
        ("Photo and banner", [(V, "What a client sees in your profile in the first seconds"), (L, "Photo and banner requirements"), (T, "Update your photo and banner")]),
        ("Headline", [(L, "A headline from your offer"), (Q, "Which headline is stronger"), (T, "Update your headline")]),
        ("About", [(V, "About teardown: before and after"), (L, "About structure: hook, proof, call to action"), (T, "Fill in your About")]),
        ("Experience with numbers", [(L, "Bringing experience bullets over from your résumé"), (T, "Fill in Experience")]),
        ("Skills and Open to work", [(L, "Skills clients find you by"), (L, "Open to work and Services"), (T, "Add skills and turn on Open to work"), (L, "Chapter wrap-up")]),
    ]),
    ("Upwork", "violet", "Account, title, overview, rate and portfolio, up to a complete profile.", "An Upwork profile at 100%", [
        ("Account and sign-in", [(V, "How Upwork works: connects, JSS, fees"), (L, "Sign-up and why profiles get rejected"), (T, "Create an account and sign in")]),
        ("Title and overview", [(V, "Overview teardown: before and after"), (L, "A title from your offer"), (L, "The first two lines of the overview"), (Q, "Which overview is stronger"), (T, "Fill in your title and overview")]),
        ("Skills and rate", [(L, "Skills and categories"), (V, "How to pick a starting rate"), (T, "Set your skills and rate")]),
        ("Upwork portfolio", [(L, "How to present a case in your portfolio"), (T, "Add three cases")]),
        ("Profile at 100%", [(L, "Verification, languages and video intro"), (T, "Bring your profile to 100%"), (L, "Chapter wrap-up")]),
    ]),
    ("Fiverr", "green", "One gig, three packages, published.", "A published Fiverr gig with three packages", [
        ("Seller account", [(V, "How Fiverr differs from Upwork"), (L, "Seller profile"), (T, "Create a seller account")]),
        ("Gig title and category", [(L, "The gig title formula"), (L, "Category and tags"), (Q, "Which title is stronger"), (T, "Set the title and category")]),
        ("Packages and prices", [(V, "Three packages: how to build the lineup"), (L, "Starting prices and extras"), (T, "Set up packages and prices")]),
        ("Description and FAQ", [(L, "Gig description structure"), (L, "FAQ and buyer requirements"), (T, "Fill in the description and FAQ")]),
        ("Cover and publishing", [(L, "Cover and gallery"), (T, "Publish your gig"), (L, "Chapter wrap-up")]),
    ]),
    ("Proposals", "orange", "Find the right jobs, read them properly, and send proposals that get replies.", "A proposal template and five real proposals sent", [
        ("Job search and filters", [(V, "Finding jobs: screencast"), (L, "Filters and saved searches"), (T, "Save a search for your niche")]),
        ("Job post breakdown and red flags", [(L, "How to read a job post"), (L, "Client red flags"), (Q, "Apply or skip"), (T, "Break down three job posts")]),
        ("Proposal structure", [(V, "Proposal teardown: before and after"), (L, "The four parts of a proposal"), (L, "The first two lines"), (Q, "Which proposal is stronger"), (T, "Build your proposal template")]),
        ("Three proposals in the simulator", [(L, "How the simulator works"), (T, "Write three proposals in the simulator")]),
        ("Five real proposals", [(L, "When and what to apply to"), (T, "Send five real proposals"), (L, "Chapter wrap-up")]),
    ]),
    ("Client and first order", "pink", "From the first message to getting paid and asked back.", "Practiced client replies, a first call and a milestone plan", [
        ("Replying to the first message", [(L, "Speed and structure of your reply"), (L, "Questions to ask the client"), (T, "Reply to a client in the simulator")]),
        ("Practice call", [(V, "How a first call goes"), (L, "Self-intro in 60 seconds"), (L, "Common client questions"), (T, "Complete a practice call")]),
        ("Contract and milestones", [(V, "Fixed price or hourly"), (L, "Scope and milestones"), (Q, "Find the mistake in the contract"), (T, "Split a project into milestones")]),
        ("Getting paid", [(L, "Withdrawal methods"), (L, "W-8BEN and taxes"), (T, "Connect a withdrawal method")]),
        ("Review and repeat order", [(L, "How to ask for a review"), (L, "How to get a repeat order"), (T, "Write a project wrap-up message"), (L, "Course wrap-up")]),
    ]),
]

chapters = [{
    "id": "foundation", "theme": "yellow", "tier": "Foundation", "title": "Foundation: résumé and positioning",
    "blurb": "A résumé that passes the check, a niche, a one-line offer and three cases. Everything later is built from these.",
    "outcome": "A one-line offer clients understand, and three cases with numbers",
    "lessons": [CP1, CP2, CP3, CP4, CP5],
}]
for title, theme, blurb, outcome, steps in LATER:
    lessons = []
    for name, items in steps:
        task = next((t for kind, t in items if kind == T), name)
        lessons.append(checkpoint(f"{slug(title.split()[0])}-{slug(name)}", name, f"{task}.", f"{task}.", parts(*items)))
    chapters.append({"id": slug(title), "theme": theme, "tier": title, "title": title, "blurb": blurb, "outcome": outcome, "lessons": lessons})


def task(key: str, title: str, intro: str, count: int, unit: str, xp: int, tips: list[str]) -> dict:
    return {"key": key, "title": title, "intro": intro, "xp": xp,
            "action": {"type": "external_task", "key": key, "title": title, "target_count": count, "unit": unit, "tips": tips}}


DAILY = [
    task("write-5-clients", "Write to 5 potential clients", "Short, personal messages to people who could use your offer. Tick one off each time you send.", 5, "message sent", 30,
         ["Start with their problem, not your skills.", "Three sentences is enough.", "End with one easy question."]),
    task("apply-3-jobs", "Apply to 3 job posts that fit your offer", "Pick posts where your offer answers the brief. Quality over volume.", 3, "proposal sent", 25,
         ["Open with what they need, in their words.", "Mention one piece of real proof."]),
    task("follow-up-2", "Follow up with 2 people who went quiet", "One short, useful follow-up each. Then let it rest.", 2, "follow-up sent", 15,
         ["Add something new: an idea, a link, a question.", "Never just “any update?”"]),
    task("comment-3", "Leave 3 useful comments where your clients are", "On posts by people who could hire you. Add something, don't pitch.", 3, "comment posted", 15,
         ["Answer a question they asked.", "Share one concrete experience."]),
    task("ask-2-intros", "Ask 2 people you know for an introduction", "Former colleagues, classmates, friends. Tell them exactly who you help.", 2, "request sent", 20,
         ["Send them your one-line offer.", "Make saying no easy."]),
    task("save-5-posts", "Save 5 job posts that fit your offer", "Build your shortlist for tomorrow. Read the whole brief before saving.", 5, "post saved", 15,
         ["Skip posts with no clear outcome.", "Note what proof each one asks for."]),
    task("show-offer-1", "Show your offer to 1 person and ask what is unclear", "Someone outside tech is best. Listen, don't explain.", 1, "conversation had", 15,
         ["Ask: “What do you think I do?”", "Write down the words they use."]),
]

path = {
    "id": "software-development-freelancer",
    "domain": "software-development",
    "title": "Freelance software developer",
    "avatars": ["fox", "owl", "cat", "bear", "frog", "robot"],
    "more_coming": "More chapters are on the way: pricing your work, repeat clients and raising your rate.",
    "achievements": [
        {"key": "first-step", "title": "First Step", "description": "Completed your first checkpoint.", "trigger": {"type": "lesson_completed", "lesson_id": "upload-your-resume"}},
        {"key": "niche-found", "title": "Niche Found", "description": "Picked a niche you can prove.", "trigger": {"type": "asset_created", "asset_type": "freelancer_niche"}},
        {"key": "identity-created", "title": "Identity Created", "description": "Saved a one-line offer.", "trigger": {"type": "asset_created", "asset_type": "freelancer_offer"}},
        {"key": "proof-ready", "title": "Proof Ready", "description": "Saved three cases with numbers.", "trigger": {"type": "asset_created", "asset_type": "portfolio_cases"}},
        {"key": "foundation-laid", "title": "Foundation Laid", "description": "Finished the first chapter.", "trigger": {"type": "lessons_completed_count", "count": 5}},
    ],
    "daily_challenges": DAILY,
    "chapters": chapters,
}

OUT.write_text(json.dumps(path, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
total = sum(lesson["minutes"] for chapter in chapters for lesson in chapter["lessons"])
print(f"{sum(len(c['lessons']) for c in chapters)} checkpoints, {total} minutes")
