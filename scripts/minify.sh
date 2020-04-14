#!/bin/bash
currentdir=$(pwd)

cd /opt/mutnmt
source venv/bin/activate

cd app/static/

# Compile custom Bootstrap css
>&2 echo "Compiling custom bootstrap..."
sass scss/custom.scss > scss/bootstrap.raw.css
cat scss/bootstrap.raw.css | postcss --use autoprefixer --no-map > css/bootstrap.css
rm scss/bootstrap.raw.css

# Minify css
for file in $(find css \( -name "*.*" ! -iname "*.min*" \) -type f -printf "%T@ %p\n" | sort -nr | cut -d\  -f2-)
do
    filename=$(echo $file | sed 's/\.[^.]*$//')
    cat $file | python3 -m cssmin > $filename.min.css
done

# Minify js
for file in $(find js \( -name "*.*" ! -iname "*.min*" \) -type f -printf "%T@ %p\n" | sort -nr | cut -d\  -f2-)
do
    filename=$(echo $file | sed 's/\.[^.]*$//')
    python3 -m jsmin $file > $filename.min.js
done

cd $currentdir