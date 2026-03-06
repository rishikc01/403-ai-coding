"""
CSE403 Project Team Matcher  (v2)
===================================
Assigns 72 students to project teams satisfying:
  1. Every student is assigned.
  2. Team size: preferred 6, range 4-6 (exception: 4).
  3. Students assigned to top-5 choices as much as possible.
  4. Pitchers who ranked their project #1 must be on that project.
  5. Each student gets at least one preferred teammate when possible.
"""

import csv, sys, random
from collections import defaultdict

# --- 1. DATA LOADING -----------------------------------------------------------

def clean_proj(p):
    p = p.strip() if p else ''
    if not p:
        return None
    if not p.lower().startswith('project'):
        p = 'Project ' + p
    return p

def load_students(filepath):
    students = {}
    with open(filepath, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            net_id = row['NetID'].strip()
            if not net_id:
                continue
            prefs = []
            for col in ['First (1) Choice', 'Second (2)  Choice', 'Third (3) Choice',
                        'Fourth (4) Choice', 'Fifth (5) Choice']:
                v = clean_proj(row.get(col, ''))
                if v and v not in prefs:
                    prefs.append(v)

            teammates = []
            for col in ['Team Member #1 UW NetID', 'Team Member #2 UW NetID',
                        'Team Member #3 UW NetID']:
                t = row.get(col, '').strip()
                if t and t != net_id:
                    teammates.append(t)

            students[net_id] = {
                'name': row['Name'].strip(),
                'net_id': net_id,
                'pitched': clean_proj(row.get('Project Pitched', '')),
                'prefs': prefs,
                'teammates': teammates,
            }
    return students

# --- 2. PROJECT UNIVERSE -------------------------------------------------------

def all_projects(students):
    projs = set()
    for s in students.values():
        for p in s['prefs']:
            projs.add(p)
        if s['pitched']:
            projs.add(s['pitched'])
    return sorted(projs)

def pitcher_constraints(students):
    """Projects that MUST run: pitcher ranked their own project #1."""
    pc = {}
    for nid, s in students.items():
        if s['pitched'] and s['prefs'] and s['prefs'][0] == s['pitched']:
            pc[s['pitched']] = nid
    return pc

# --- 3. PROJECT SELECTION ------------------------------------------------------

def select_projects(students):
    """
    Pick which projects to run.
    Include all mandatory pitcher projects first, then fill by demand
    until we have enough teams for the student body (target team size ~6).
    """
    n = len(students)
    min_teams = max(n // 6, 10)
    max_teams = (n + 3) // 4  # enough so no team exceeds 6

    demand = defaultdict(int)
    for s in students.values():
        for p in s['prefs']:
            demand[p] += 1

    required = set(pitcher_constraints(students).keys())

    extras = sorted(
        [p for p in demand if p not in required],
        key=lambda p: -demand[p]
    )

    selected = list(required)
    for p in extras:
        if len(selected) >= max_teams:
            break
        selected.append(p)

    while len(selected) < min_teams and extras:
        p = extras.pop(0)
        if p not in selected:
            selected.append(p)

    return sorted(selected)

# --- 4. SCORING ----------------------------------------------------------------

RANK_SCORE = {0: 10, 1: 8, 2: 5, 3: 3, 4: 1}

def pref_score(student, project):
    try:
        return RANK_SCORE[student['prefs'].index(project)]
    except (ValueError, KeyError):
        return 0

def teammate_overlap(student, team_members):
    return sum(1 for t in student['teammates'] if t in team_members)

# --- 5. ASSIGNMENT -------------------------------------------------------------

def assign(students, selected_projects, seed=42):
    random.seed(seed)
    teams = {p: [] for p in selected_projects}
    remaining = set(students.keys())
    pc = pitcher_constraints(students)

    # Step A: place mandatory pitchers
    for proj, nid in pc.items():
        if proj in teams and nid in remaining:
            teams[proj].append(nid)
            remaining.remove(nid)

    # Step B: most-constrained first (fewest of their prefs are in selected)
    def options_count(nid):
        return sum(1 for p in students[nid]['prefs'] if p in teams)

    order = sorted(remaining, key=lambda nid: (options_count(nid), random.random()))

    for nid in order:
        s = students[nid]
        best_proj, best_score = None, -999

        for proj in selected_projects:
            if len(teams[proj]) >= 6:
                continue
            ps = pref_score(s, proj)
            ts = teammate_overlap(s, set(teams[proj]))
            size_penalty = max(0, len(teams[proj]) - 4)
            score = ps * 3 + ts * 4 - size_penalty
            if score > best_score:
                best_score = score
                best_proj = proj

        if best_proj is None:
            best_proj = min(selected_projects, key=lambda p: len(teams[p]))

        teams[best_proj].append(nid)
        remaining.discard(nid)

    return teams

# --- 6. FIX SIZES -------------------------------------------------------------

def fix_sizes(teams, students, selected_projects, min_sz=4, max_sz=6):
    projects = [p for p in selected_projects if p in teams]

    for _ in range(200):
        small = [p for p in projects if p in teams and 0 < len(teams[p]) < min_sz]
        large = [p for p in projects if p in teams and len(teams[p]) > max_sz]

        if not small and not large:
            break

        for big_p in large:
            while len(teams[big_p]) > max_sz:
                student = teams[big_p][-1]
                s = students[student]
                candidates = sorted(
                    [p for p in projects if p != big_p and len(teams[p]) < max_sz],
                    key=lambda p: -pref_score(s, p)
                )
                if candidates:
                    teams[big_p].remove(student)
                    teams[candidates[0]].append(student)
                else:
                    break

        for sm_p in small:
            while teams[sm_p]:
                student = teams[sm_p][0]
                s = students[student]
                candidates = sorted(
                    [p for p in projects if p != sm_p and len(teams[p]) < max_sz],
                    key=lambda p: (-pref_score(s, p), len(teams[p]))
                )
                if candidates:
                    teams[sm_p].remove(student)
                    teams[candidates[0]].append(student)
                else:
                    fallback = min((p for p in projects if p != sm_p),
                                   key=lambda p: len(teams[p]))
                    teams[sm_p].remove(student)
                    teams[fallback].append(student)

        for p in list(projects):
            if p in teams and len(teams[p]) == 0:
                del teams[p]
                projects.remove(p)

    return teams, projects

# --- 7. EVALUATION ------------------------------------------------------------

def evaluate(teams, students):
    pc = pitcher_constraints(students)
    total = in_top5 = 0
    sum_ps = sum_ts = 0
    tm_sat = tm_tot = 0
    p_ok = p_tot = 0

    for proj, members in teams.items():
        mset = set(members)
        for nid in members:
            s = students[nid]
            ps = pref_score(s, proj)
            ts = teammate_overlap(s, mset - {nid})
            sum_ps += ps
            sum_ts += ts
            if ps > 0:
                in_top5 += 1
            total += 1
            if s['teammates']:
                tm_tot += 1
                if any(t in mset for t in s['teammates']):
                    tm_sat += 1

    for proj, nid in pc.items():
        p_tot += 1
        if proj in teams and nid in teams[proj]:
            p_ok += 1

    return {
        'total': total,
        'in_top5_pct': round(100 * in_top5 / total, 1) if total else 0,
        'avg_pref': round(sum_ps / total, 2) if total else 0,
        'avg_tm': round(sum_ts / total, 2) if total else 0,
        'pitcher': f"{p_ok}/{p_tot}",
        'teammate_pct': round(100 * tm_sat / tm_tot, 1) if tm_tot else 0,
    }

# --- 8. OUTPUT ----------------------------------------------------------------

def print_results(teams, students, projects):
    pc = pitcher_constraints(students)
    print("\n" + "="*68)
    print("  CSE403 PROJECT TEAM ASSIGNMENTS")
    print("="*68)

    for proj in sorted(projects):
        if proj not in teams:
            continue
        members = teams[proj]
        tag = "  [PITCHER PROJECT]" if proj in pc else ""
        print(f"\n  {proj}{tag}  |  {len(members)} members")
        print("  " + "-"*60)
        for nid in sorted(members):
            s = students[nid]
            rank = s['prefs'].index(proj) + 1 if proj in s['prefs'] else None
            rank_str = f"rank #{rank}" if rank else "not in top 5"
            tms = [t for t in s['teammates'] if t in set(members)]
            tm_str = f"  | teammates: {', '.join(tms)}" if tms else ""
            pitcher_str = " [PITCHER]" if pc.get(proj) == nid else ""
            print(f"    {s['name']:<22} ({nid})  [{rank_str}]{tm_str}{pitcher_str}")

    m = evaluate(teams, students)
    print(f"\n{'='*68}")
    print("  QUALITY METRICS")
    print(f"{'='*68}")
    print(f"  Students assigned           : {m['total']}/72")
    print(f"  Assigned to top-5 project   : {m['in_top5_pct']}%")
    print(f"  Avg preference score        : {m['avg_pref']} / 10")
    print(f"  Avg preferred teammates     : {m['avg_tm']}")
    print(f"  Pitcher constraints met     : {m['pitcher']}")
    print(f"  Has >= 1 preferred teammate : {m['teammate_pct']}%")

    viol = [(p, len(teams[p])) for p in projects
            if p in teams and not (4 <= len(teams[p]) <= 6)]
    if viol:
        print(f"\n  SIZE VIOLATIONS: {viol}")
    else:
        print(f"\n  All {len(teams)} teams are valid size (4-6)")


def save_csv(teams, students, projects, out_path):
    pc = pitcher_constraints(students)
    rows = []
    for proj in sorted(projects):
        if proj not in teams:
            continue
        for nid in sorted(teams[proj]):
            s = students[nid]
            rank = s['prefs'].index(proj) + 1 if proj in s['prefs'] else 'N/A'
            tms = [t for t in s['teammates'] if t in set(teams[proj]) and t != nid]
            rows.append({
                'Project': proj,
                'Team Size': len(teams[proj]),
                'NetID': nid,
                'Name': s['name'],
                'Preference Rank': rank,
                'Is Pitcher': 'Yes' if pc.get(proj) == nid else 'No',
                'Preferred Teammates in Team': ', '.join(tms),
            })
    with open(out_path, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"\n  Saved to: {out_path}")


def save_readme(out_path):
    readme = """# CSE403 Team Matcher

## Overview
Automatically assigns students to project teams for CSE403 based on:
- Project preferences (ranked 1-5)
- Preferred teammates
- Pitcher constraints (must be on their own project if it's their #1 choice)
- Team size requirements: 4-6 students (preferred: 6)

## Requirements
- Python 3.7+
- No external libraries required (uses only: csv, sys, random, collections)

## How to Run
```bash
python3 team_matcher.py <input_csv> [output_csv]
```

### Example
```bash
python3 team_matcher.py GenAI-InputFile_-_ProjectPreferences.csv team_assignments.csv
```

If no output file is specified, defaults to `team_assignments.csv`.

## Input Format
A CSV file with the following columns:
| Column | Description |
|--------|-------------|
| Name | Student full name |
| NetID | Student UW NetID |
| Project Pitched | Project the student pitched (if any) |
| First (1) Choice | Top project preference |
| Second (2) Choice | 2nd preference |
| Third (3) Choice | 3rd preference |
| Fourth (4) Choice | 4th preference |
| Fifth (5) Choice | 5th preference |
| Team Member #1 UW NetID | Preferred teammate 1 (NetID) |
| Team Member #2 UW NetID | Preferred teammate 2 (NetID) |
| Team Member #3 UW NetID | Preferred teammate 3 (NetID) |

## Output
A CSV (`team_assignments.csv`) with columns:
- Project, Team Size, NetID, Name, Preference Rank, Is Pitcher, Preferred Teammates in Team

Console output shows the full assignment with rankings and teammate overlaps, plus quality metrics.

## Algorithm Summary
1. **Data Cleaning**: Normalize project names (e.g., "EasyBook" -> "Project EasyBook"), strip whitespace, remove self-references in teammate fields.
2. **Project Selection**: Always include projects where a pitcher ranked their own pitch #1. Fill remaining slots by demand (most popular projects first) until team count is appropriate.
3. **Greedy Assignment**:
   - Mandatory pitchers placed first.
   - Remaining students sorted by how few of their preferred projects are available (most-constrained first).
   - Each student scored per project: `3 * preference_score + 4 * teammate_overlap - size_penalty`
   - Fallback: least-full team.
4. **Size Correction**: Iterative redistribution to ensure all teams are 4-6 members.
5. **Quality Report**: % in top-5, average preference score (max 10), teammate satisfaction, pitcher constraint compliance.

## Data Cleaning Notes Applied to Input File
- "EasyBook" normalized to "Project EasyBook"
- Student 72 has no preference data; assigned by fallback (least-full team)
- Self-references in teammate fields ignored (e.g., student8 listed themselves)
- "aidanyu" referenced by student10 is not in the student roster; ignored
"""
    with open(out_path, 'w') as f:
        f.write(readme)
    print(f"  README saved to: {out_path}")


# --- 9. MAIN ------------------------------------------------------------------

if __name__ == '__main__':
    inp = sys.argv[1] if len(sys.argv) > 1 else 'GenAI-InputFile_-_ProjectPreferences.csv'
    out = sys.argv[2] if len(sys.argv) > 2 else 'team_assignments.csv'

    print("CSE403 Team Matcher v2")
    print("-" * 40)
    print(f"Input: {inp}")

    students = load_students(inp)
    print(f"Loaded {len(students)} students")

    print("\nData cleaning notes:")
    print("  'EasyBook' -> 'Project EasyBook'")
    print("  Student 72 has no preferences (fallback assignment)")
    print("  Self-references in teammate lists removed")
    print("  'aidanyu' (student10's teammate) not in roster, ignored")

    pc = pitcher_constraints(students)
    print(f"\nMandatory pitcher projects ({len(pc)}):")
    for p, nid in sorted(pc.items()):
        print(f"  {p} <- {students[nid]['name']} ({nid})")

    selected = select_projects(students)
    print(f"\nSelected {len(selected)} projects:")
    for p in selected:
        mark = " [PITCHER]" if p in pc else ""
        print(f"  {p}{mark}")

    teams = assign(students, selected)
    teams, final_projects = fix_sizes(teams, students, selected)

    print_results(teams, students, final_projects)
    save_csv(teams, students, final_projects, out)
    save_readme('README.md')