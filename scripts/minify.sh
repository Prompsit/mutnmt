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
for file in $(ls css -I "*.min*")
do
    filename=$(echo $file | sed 's/\.[^.]*$//')
    cat css/$file | python3 -m cssmin > css/$filename.min.css
done

# Minify js
for file in $(ls js -I "*.min*")
do
    filename=$(echo $file | sed 's/\.[^.]*$//')
    python3 -m jsmin js/$file > js/$filename.min.js
done

cd $currentdir