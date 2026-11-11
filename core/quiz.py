"""Interest quiz: 8 tap-to-answer questions -> top career clusters. Pure code, no model, no network.
Uses the 16 national Career Clusters as the categories. Descriptions are general and student-friendly."""

from __future__ import annotations

# key: (name, friendly description, search keywords, example careers)
CLUSTERS = {
    "AG": ("Agriculture, Food & Natural Resources", "Growing food, caring for animals, and protecting land, water, and wildlife.", "agriculture environment animals", "farmer, park ranger, wildlife biologist"),
    "AC": ("Architecture & Construction", "Designing and building homes, bridges, and cities.", "architecture construction building", "architect, electrician, civil engineer"),
    "AR": ("Arts, Media & Communication", "Telling stories and creating art, music, video, and design.", "art design media", "graphic designer, journalist, sound engineer"),
    "BM": ("Business & Management", "Leading teams and organizations and helping them succeed.", "business management entrepreneurship", "manager, entrepreneur, human resources specialist"),
    "ED": ("Education & Training", "Teaching, coaching, and helping people learn.", "teaching education coaching", "teacher, school counselor, coach"),
    "FI": ("Finance", "Working with money: saving, investing, banking, and insurance.", "finance accounting investing", "financial analyst, accountant, banker"),
    "GV": ("Government & Public Service", "Serving communities by running public programs and making laws.", "government public service policy", "city planner, policy analyst, diplomat"),
    "HS": ("Health Science", "Caring for people's health in clinics, hospitals, and labs.", "health medicine healthcare", "nurse, physical therapist, lab technician"),
    "HT": ("Hospitality & Tourism", "Making travel, food, and events great for guests.", "hospitality tourism events", "chef, event planner, hotel manager"),
    "HU": ("Human Services", "Supporting families and communities through counseling and social work.", "social work counseling community", "social worker, counselor, childcare director"),
    "IT": ("Information Technology", "Building and protecting software, apps, and networks.", "computer science software technology", "software developer, cybersecurity analyst, network administrator"),
    "LW": ("Law, Public Safety & Security", "Keeping communities safe and fair.", "law public safety", "firefighter, paralegal, police officer"),
    "MF": ("Manufacturing", "Making products with machines, robots, and tools.", "manufacturing robotics machining", "machinist, robotics technician, quality inspector"),
    "MK": ("Marketing & Sales", "Helping people discover products and ideas they will love.", "marketing sales advertising", "marketing manager, brand designer, sales representative"),
    "ST": ("Science, Technology, Engineering & Math", "Using science and math to explore, invent, and solve problems.", "science engineering math", "engineer, data scientist, research scientist"),
    "TR": ("Transportation & Logistics", "Moving people and goods by road, air, rail, and sea.", "transportation logistics aviation", "pilot, logistics coordinator, diesel technician"),
}

# Each question: (text, [(answer, {cluster: points})])
QUESTIONS = [
    ("On a free Saturday, what sounds most fun?", [
        ("Building or fixing something", {"AC": 2, "MF": 2, "TR": 1, "ST": 1}),
        ("Running experiments or figuring out how things work", {"ST": 2, "HS": 1, "IT": 1}),
        ("Drawing, filming, writing, or making music", {"AR": 3, "MK": 1}),
        ("Helping or teaching someone", {"HU": 2, "ED": 2, "HS": 1})]),
    ("Which class do you like most?", [
        ("Math or economics", {"FI": 2, "ST": 1, "BM": 1, "IT": 1}),
        ("Science", {"ST": 2, "HS": 2, "AG": 1}),
        ("Art, music, or English", {"AR": 2, "ED": 1, "MK": 1}),
        ("Social studies or government", {"GV": 2, "LW": 2, "HU": 1})]),
    ("In a group project, you are usually...", [
        ("The leader who organizes everyone", {"BM": 2, "GV": 1, "ED": 1, "HT": 1}),
        ("The idea person who designs how it looks", {"AR": 1, "MK": 2, "ST": 1, "AC": 1}),
        ("The one who checks facts and does the research", {"ST": 1, "LW": 1, "FI": 1, "GV": 1}),
        ("The one who gets the tools or computers working", {"IT": 2, "MF": 1, "TR": 1, "AC": 1})]),
    ("Where would you most like to work?", [
        ("Outdoors: a farm, a park, or a building site", {"AG": 2, "AC": 1, "TR": 1}),
        ("A lab or a hospital", {"HS": 2, "ST": 2}),
        ("An office or on a computer", {"IT": 2, "FI": 1, "BM": 1, "MK": 1}),
        ("Out and about with people: restaurants, hotels, events, travel", {"HT": 2, "MK": 1, "HU": 1, "TR": 1})]),
    ("Which problem would you most like to help solve?", [
        ("Keeping food, water, and nature healthy", {"AG": 2, "ST": 1, "HS": 1}),
        ("Keeping people safe and treated fairly", {"LW": 2, "GV": 2, "HU": 1}),
        ("Helping people stay healthy", {"HS": 3, "HU": 1}),
        ("Making cool products or apps", {"IT": 2, "MF": 1, "ST": 1, "MK": 1})]),
    ("What sounds the most interesting?", [
        ("Saving, investing, and understanding money", {"FI": 3, "BM": 1}),
        ("Selling or convincing people to try something new", {"MK": 3, "BM": 1, "HT": 1}),
        ("Planning how to move things: trucks, planes, packages", {"TR": 3, "MF": 1}),
        ("Building things that last: homes, bridges, machines", {"AC": 2, "MF": 2, "ST": 1})]),
    ("What would you most like to do?", [
        ("Teach or coach", {"ED": 3, "HU": 1}),
        ("Create something people see or hear", {"AR": 3, "MK": 1}),
        ("Run a business or be my own boss", {"BM": 2, "FI": 1, "MK": 1, "HT": 1}),
        ("Explore and invent new things", {"ST": 3, "IT": 1})]),
    ("Which one sounds best?", [
        ("Planning trips, events, or great experiences", {"HT": 3, "MK": 1}),
        ("Speaking up for others or leading a community", {"GV": 2, "HU": 1, "LW": 1}),
        ("Growing food or protecting animals and nature", {"AG": 3, "HS": 1}),
        ("Working with robots, code, or networks", {"IT": 2, "MF": 1, "ST": 1})]),
]


def score(answers: list[int], top: int = 3) -> list[dict]:
    """answers: chosen option index per question (None/out of range = skipped). Returns the top clusters,
    ties broken by the order above so the result is always the same for the same answers."""
    points = {k: 0 for k in CLUSTERS}
    for (_, options), choice in zip(QUESTIONS, answers):
        if isinstance(choice, int) and 0 <= choice < len(options):
            for cluster, pts in options[choice][1].items():
                points[cluster] += pts
    order = list(CLUSTERS)
    ranked = sorted((k for k in CLUSTERS if points[k] > 0), key=lambda k: (-points[k], order.index(k)))[:top]
    return [{"key": k, "name": CLUSTERS[k][0], "blurb": CLUSTERS[k][1], "keywords": CLUSTERS[k][2],
             "examples": CLUSTERS[k][3], "points": points[k]} for k in ranked]


def summary(top: list[dict]) -> str:
    """Markdown card for the result (general information from the quiz, not from web sources)."""
    lines = ["**Your top career clusters** (from your quiz answers)"]
    for i, c in enumerate(top, 1):
        lines.append(f"{i}. **{c['name']}**: {c['blurb']} Example jobs: {c['examples']}.")
    return "\n".join(lines)
