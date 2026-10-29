import urllib.request
import json

# Fetch dumps/leagues
req_l = urllib.request.Request('https://play.soccerverse.com/datacentre/dumps/leagues', headers={'User-Agent': 'SoccerverseTool/1.0'})
with urllib.request.urlopen(req_l) as res:
    leagues_data = json.loads(res.read().decode('utf-8'))

fields = leagues_data['meta']['fields']
leagues = leagues_data['data']

# Fetch bootstrap
req_b = urllib.request.Request('https://play.soccerverse.com/v1/bootstrap', headers={'User-Agent': 'SoccerverseTool/1.0'})
with urllib.request.urlopen(req_b) as res:
    bootstrap = json.loads(res.read().decode('utf-8'))

assocs = {a['country_id']: a for a in bootstrap['associations']['national']}

by_country = {}
for lid, lval in leagues.items():
    row = dict(zip(fields, lval))
    cid = row['country_id']
    if cid not in by_country:
        by_country[cid] = []
    by_country[cid].append(row)

country_list = []

for cid, llist in by_country.items():
    sorted_leagues = sorted(llist, key=lambda x: int(x['level']))
    top_league = sorted_leagues[0]

    ticket_cost_scaled = top_league['ticket_cost']
    ticket_cost_svc = ticket_cost_scaled / 10000.0
    ave_attendance = top_league['ave_attendance']
    ave_club_rating = top_league['ave_club_rating_start']

    num_divisions = len(sorted_leagues)
    total_clubs = sum(l['num_teams'] for l in sorted_leagues)
    div1_clubs = top_league['num_teams']

    div1_tv_money_svc = top_league['tv_money'] / 10000.0
    total_tv_money_svc = sum(l['tv_money'] for l in sorted_leagues) / 10000.0
    div1_prize_pot_svc = top_league['prize_money_pot'] / 10000.0
    total_prize_pot_svc = sum(l['prize_money_pot'] for l in sorted_leagues) / 10000.0

    assoc = assocs.get(cid, {})
    match_time = f"{assoc.get('match_time_hours', 0):02d}:{assoc.get('match_time_minutes', 0):02d} UTC"

    country_list.append({
        'country_code': cid,
        'ticket_cost_svc': ticket_cost_svc,
        'ticket_cost_scaled': ticket_cost_scaled,
        'ave_attendance': ave_attendance,
        'ave_club_rating': ave_club_rating,
        'num_divisions': num_divisions,
        'total_clubs': total_clubs,
        'div1_clubs': div1_clubs,
        'div1_tv_money_svc': div1_tv_money_svc,
        'total_tv_money_svc': total_tv_money_svc,
        'div1_prize_pot_svc': div1_prize_pot_svc,
        'total_prize_pot_svc': total_prize_pot_svc,
        'match_time': match_time
    })

# Sort descending by Div 1 Ticket Price
country_list.sort(key=lambda x: x['ticket_cost_svc'], reverse=True)

# Write Markdown file
with open('soccerverse_countries.md', 'w') as f:
    f.write("# Soccerverse Countries Overview\n\n")
    f.write("All 154 available countries in Soccerverse, sorted by Division 1 Ticket Price (descending).\n\n")
    f.write("| Rank | Country | Ticket Price (SVC) | Ave Attendance | Div 1 Rating | Divisions | Total Clubs | Div 1 TV Money (SVC) | Div 1 Prize Pot (SVC) | Kickoff Time (UTC) |\n")
    f.write("|---|---|---|---|---|---|---|---|---|---|\n")
    for i, c in enumerate(country_list, 1):
        f.write(f"| {i} | `{c['country_code']}` | {c['ticket_cost_svc']:,.2f} | {c['ave_attendance']:,} | {c['ave_club_rating']} | {c['num_divisions']} | {c['total_clubs']} | {c['div1_tv_money_svc']:,.2f} | {c['div1_prize_pot_svc']:,.2f} | {c['match_time']} |\n")

print(f"Generated soccerverse_countries.md with {len(country_list)} rows.")
