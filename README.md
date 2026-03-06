# CSE403 Team Matcher

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