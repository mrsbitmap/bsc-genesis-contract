with open('soccerverse_countries.md') as f:
    lines = [line.strip() for line in f if line.startswith('|') and not line.startswith('| Rank') and not line.startswith('|---')]

print(f'Found {len(lines)} data rows in table.')

prices = []
for line in lines:
    parts = [p.strip() for p in line.split('|')[1:-1]]
    rank = int(parts[0])
    country = parts[1].replace('`', '')
    price = float(parts[2].replace(',', ''))
    prices.append(price)

is_sorted = all(prices[i] >= prices[i+1] for i in range(len(prices)-1))
print(f'Sorting check (descending): {is_sorted}')
print(f'Highest price: {prices[0]} SVC')
print(f'Lowest price: {prices[-1]} SVC')
assert len(lines) == 154, f'Expected 154 rows, got {len(lines)}'
assert is_sorted, 'Table is not properly sorted by ticket price!'
print('Validation test passed successfully!')
