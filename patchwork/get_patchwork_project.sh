#!/bin/bash

get_patchwork_project()
{
	local PAGE=$1

	cd project
	wget "https://patchwork.kernel.org/api/projects/?page=${PAGE}" -O projects_list.json -o /dev/null

	if [ $? -ne 0 ]; then
		return 1
	fi

	#jq -rc '.[] | (.id,.name)' projects_list.json
	jq -c ".[]" projects_list.json | while read project;
	do
		ID=`echo ${project} | jq -r ".id"`
		NAME=`echo ${project} | jq -r ".name"`
		echo "| " $ID " | " $NAME " |" | tee -a projects_list.md
	done

	cd ..

	return 0
}


echo "| ID | PROJECT |" | tee projects_list.md
echo "|:--:|:-------:|" | tee -a projects_list.md

if [ ! -d "project" ]; then
	mkdir project
fi

for i in `seq 1 10`
do
	get_patchwork_project $i
	if [ $? -ne 0 ]; then
		break
	fi
done
