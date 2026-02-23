import re
p = re.compile("*.log".replace("*", ".*"))
print(p.match("4. Catalog-Ống.pdf"))
