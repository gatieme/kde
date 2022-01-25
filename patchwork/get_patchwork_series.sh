#!/bin/bash

set -e
# demo: sh ./get_patchwork_series.sh -p 365 -d 2022-01-25


get_object_by_id()
{
	local ID=$1
	local KEY="$2"
	if [ $# -eq 3 ]; then
		local SUBKEY=$3
	fi
	OBJECT=`cat series_${ID}.json | jq -r ".${KEY}"`
	if [ "${OBJECT}" = "null" ] ; then
		OBJECT=`cat series_${ID}.json | jq -r ".${SUBKEY}"`
	fi

	echo "${OBJECT}"
}

object_to_directory()
{
	local OBJECT=$1
	DIR=`echo "${OBJECT}" | sed "s/\[//g" | sed "s/\]//g" | sed "s/://g" | sed "s/\///g" | sed "s/ /_/g"`

	echo "${DIR}"
}

get_patchwork_project()
{
	local PROJECT_ID=$1
	local PROJECT_NAME

	if [ ! -d "project" ]; then
		mkdir project
	fi
	cd project
	wget https://patchwork.kernel.org/api/projects/${PROJECT_ID}/ -O project_${PROJECT_ID}.json -o /dev/null
	PROJECT_NAME=`jq -r ".name" project_${PROJECT_ID}.json`
	cd ..
	echo "${PROJECT_NAME}"
}

get_patchwork_series_day()
{
	local PROJECT_ID=$1
	local DAY=$2
	local PROJECT_NAME=`get_patchwork_project ${PROJECT_ID}`

	echo "check <${PROJECT_NAME}> mailing-list series on ${DAY}"

	cd ${DAY}
	if [ ! -f "${DAY}_series.json" ]; then
		wget "https://patchwork.kernel.org/api/series/?project=${PROJECT_ID}&archive=both&format=json&before=${DAY}T23%3A59%3A59&since=${DAY}T00%3A00%3A00" -O ${DAY}_series.json -o /dev/null
	fi

	num=`cat ${DAY}_series.json | jq '. | length'`
	if [ ${num} -eq 0 ]
	then
		echo "${DAY} is NULL"
		cd ..
		rm -rf ${DAY}
		exit
	fi

	echo "| 时间  | 作者 | 特性 | 描述 | 是否合入主线 | 链接 |" | tee -a ${DAY}.md
	echo "|:-----:|:----:|:----:|:----:|:------------:|:----:|" | tee -a ${DAY}.md

	cat ${DAY}_series.json | jq '.[]' | jq '.id' | while read ID
	do
		if [ ! -d "${ID}" ]; then
			mkdir ${ID}
		fi
		cd ${ID}
		if [ ! -f "series_${ID}.json" ]; then
			wget "https://patchwork.kernel.org/api/series/${ID}/?format=json&archive=both" -O series_${ID}.json -o /dev/null
		fi

		DATE=`echo ${DAY} | sed "s/-/\//g"`
		SUBJECT=`get_object_by_id ${ID} "name"`
		VERSION=`get_object_by_id ${ID} "version"`
		TOTAL=`get_object_by_id ${ID} "total"`
		AUTHOR=`get_object_by_id ${ID} "submitter.name" "submitter.email"`
		EMAIL=`get_object_by_id ${ID} "submitter.email"`
		WEB_URL=`get_object_by_id ${ID} "cover_letter.web_url" "patches[0].web_url"`
		LIST_ARCHIVE_URL=`get_object_by_id ${ID} "cover_letter.list_archive_url" "patches[0].list_archive_url"`

		cd ..
		echo "| ${DATE} | ${AUTHOR} <${EMAIL}> | [${SUBJECT}](${WEB_URL}) | ${ID} | v${VERSION} ☐☑ | [PatchWork v${VERSION},0/${TOTAL}](${LIST_ARCHIVE_URL}) |" | tee -a ${DAY}.md
		DIRECTORY=`object_to_directory "${SUBJECT}"`
		mv ${ID} ${ID}_${DIRECTORY}
		cd ${ID}_${DIRECTORY}

		num=`cat series_${ID}.json | jq '. | length'`
		if [ ${num} -eq 0 ]
		then
			echo "series_${ID}.json is NULL"
			cd ..
			rm -rf ${ID}
			exit
		fi

		mbox=`cat series_${ID}.json | jq -r '.mbox'`
		wget "$mbox" -O series_${ID}.patch -o /dev/null

		if [ -f "wget-log" ]; then
			rm wget-log
			exit
		fi
		cd ..

		FILE="overview_series_${DAY}.md"
		if [ -f "${FILE}" ]; then
		rm ${FILE}
		fi
		touch ${FILE}

		for ID in `ls -1 */*.patch`
		do
			FLINE=`cat ${ID} | grep -n -m 1 "X-Virus-Scanned: ClamAV using ClamSMTP" | head -n1 | awk -F ':' '{ print $1 }'`
			TLINE=`cat ${ID} | grep -n -m 1 "\-\-\- a" | head -n1 | awk -F ':' '{ print $1 }'`
			NAME=`cat ${ID} | grep  -m 1 "From: " | head -n1`
			SUBJECT=`cat ${ID} | grep -m 1 "Subject: " | head -n1 | sed 's/Subject: //g'`
			SUBLINE=`cat ${ID} | grep -n -m 1 "Subject: " | head -n1 | awk -F ':' '{ print $1 }'`
			k=`expr ${SUBLINE} + 1`
			IF=`sed -n "${k}p" ${ID}`

			a=`echo ${IF} | grep -v "Date: " | grep -v "Message-ID:" | wc -l`
			if [ ${a} -eq 1 ]
			then
				echo "#### ${SUBJECT}${IF}" >> ${FILE}
			else
				echo "#### ${SUBJECT}" >> ${FILE}
			fi
			echo "##### ${NAME}\n" >> ${FILE}
			echo "\`\`\`c" >> ${FILE}
			f=`expr ${FLINE} + 2`
			b=`cat ${ID} | grep -n -m 1 "\-\-\- a" | wc -l`
			if [ ${b} -eq 0 ]
			then
				t=`cat ${ID} | wc -l`
			else
				t=`expr ${TLINE} - 3`
			fi
			sed -n -e "${f},${t}p" ${ID}  >> ${FILE}
			# tail -n +${k} ${ID} >> ${FILE}
			echo "\`\`\`" >> ${FILE}
		done
	done
}

get_patchwork_cover_day()
{
	local PROJECT_ID=$1
	local DAY=$2

	cd ${DAY}

	# cover_letter
	wget "https://patchwork.kernel.org/api/covers/?project=${PROJECT_ID}&format=json&archive=both&before=${DAY}T23%3A59%3A59&since=${DAY}T00%3A00%3A00" -O covers.json -o /dev/null

	num=`cat covers.json | jq '. | length'`
	if [ ${num} -eq 0 ]
	then
		echo "${DAY} is NULL"
		cd ..
		exit
	fi

	cat covers.json | jq '.[]' | jq '.id' | while read q
	do
		if [ ! -f "${q}.patch" ]; then
			wget "https://patchwork.kernel.org/cover/${q}/mbox/" -O ${q}_cover_letter.patch -o /dev/null
		fi
	done
	exit 0
	FILE="overview_covers_${DAY}.md"
	if [ -f "${FILE}" ]; then
		rm ${FILE}
	fi
	touch ${FILE}
	echo "\n" >> ${FILE}
	# i=1
	for w in `ls -1 *.patch`
	do
		LINE=`cat ${w} | grep -n "X-Virus-Scanned" | awk -F ':' '{ print $1 }'`
		NAME=`cat ${w} | grep "From: "`
		SUBJECT=`cat ${w} | grep "Subject: " | sed 's/Subject: //g'`
		echo "#### ${SUBJECT}" >> ${FILE}
		echo "##### ${NAME}\n" >> ${FILE}
		echo "\`\`\`c" >> ${FILE}
		k=`expr ${LINE} + 1`
		tail -n +${k} ${w} >> ${FILE}
		echo "\`\`\`" >> ${FILE}
		# i=`expr $i + 1`
	done
	# rm *.patch
cd ..
}

while getopts "p:d:" arg #选项后面的冒号表示该选项需要参数
do
	case $arg in
	d)
		date=$OPTARG
		if  [ ! -n "$date" ] ;then
			DAY=`date +"%Y-%m-%d"`
		else
			DAY=$OPTARG
		fi

		mkdir -p series/${PROJECT_ID}/${DAY}
		cd series/${PROJECT_ID}
		get_patchwork_series_day ${PROJECT_ID} ${DAY}
		#get_patchwork_cover_day ${DAY}
	;;

	p)
		PROJECT_ID=$OPTARG
		;;
	?)  #当有不认识的选项的时候arg为?
	echo "unkonw argument"
		exit 1
	;;
	esac
done

# cat *.patch | grep "Subject: " > patches.list
# sed 's/Subject: /* /g' patches.list | sort -k 3 -r >> ${FILE}
# cat */*.json | jq '.[] | { Patch: .name, From: .submitter.name, Email: .submitter.email}'
