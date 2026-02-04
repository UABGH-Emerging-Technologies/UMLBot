#!/bin/bash
# Define your variables here
project_name="UMLBot"
author="Ryan Godwin"
author_email="ryangodwin@uabmc.edu"
repository_url="https://github.com/UABGH-Emerging-Technologies/UMLBot"
data_dir="data"
data_directory_name="DATASCI"

echo "Initialize Git"
cd $project_name
pwd
git init

echo "Setting Config"
git config user.name $author
git config user.email $author_email

echo "Updating Origin"
git remote add origin $repository_url
git fetch
git pull origin master
mv $data_directory_name $data_dir
git add .
git commit -m 'initializing from copier'
git push -u origin HEAD

echo "Importing LLM Utils"
git submodule add https://github.com/UABPeriopAI/llm_utils.git
git submodule update --init --recursive
cd llm_utils
git checkout main
cd ..
git add .
git commit -m 'updating llm_utils'
git push -u origin HEAD

echo "Merging and deleting template"
git branch -M master feature/initialize_template
git push -d origin master    
git branch -d master
git push origin HEAD