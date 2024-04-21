#!/bin/bash

### Prepare part ###
old_version=${1//\./\\.}  # Replace dot with escaped dot
new_version=$2

declare -a files=(
    "web/src/beepy.js" "web/package.json"
    "beepy/framework.py"
    "beepy/dev/example.html" "docs/live-examples.md"
)

# Update version in main files
for file in "${files[@]}"; do
    sed -i "s/$old_version/$new_version/g" $file
done

### JS part ###
cd web
# Update version in package-lock.json
npm i
# Create dist/beepy.js
npm run build
# Temporary copy README.md  +  Actual publishing
cp ../README.md . && npm publish && rm README.md
cd ..


### Python part ###
# Create dist/* files
hatch build
# Actual publishing
twine upload "dist/*$new_version[-.]*"
