import re

# Regex for training log analysis
training_regex = r'^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}),\d+\s+(\-\s+\w+\s)*(-\s+)*Epoch\s+(\d+),?\sStep:\s+(\d+),?\s+Batch Loss:\s+(\d+.\d+),?\s+Tokens per Sec:\s+(\d+),\s+Lr:\s+(\d+.\d+)$'
validation_regex = r'^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2},\d+)\s(\w|\s|\(|\)|\-)+(\d+),\s+step\s*(\d+):\s+bleu:\s+(\d+\.\d+),\s+loss:\s+(\d+\.\d+),\s+ppl:\s+(\d+\.\d+),\s+duration:\s+(\d+.\d+)s$'
re_flags = re.IGNORECASE | re.UNICODE