#!/bin/bash



get_series_from_file()
{
	local COVER_FILE=$1
	#COVER_NAME=`$(basename "${COVER_FILE}" .cove)`
	#echo ${COVER_NAME}

	#Subject: [PATCH 0/6] sched,numa: weigh nearby nodes for task placement on complex NUMA topologies (v2)
	#From: riel@redhat.com <riel@redhat.com>
	#Date: Fri, 17 Oct 2014 03:29:48 -0400
	#Message-Id: <1413530994-9732-1-git-send-email-riel@redhat.com>
	#cat ${COVER_FILE} | grep "Subject" | sed 's/Subject: //g' # sed -r 's/Subject: (.*)/\1/'

	#SUBJECT=`cat ${COVER_FILE}    | grep "Subject"	    | sed -r 's/Subject: (.*)/\1/'`
	SUBJECT=`cat ${COVER_FILE}    | grep "Subject"	    | head -n 1 | sed -r 's/Subject: \[PATCH(.*)\] (.*)/\2/'`


	VERSION=`cat ${COVER_FILE}    | grep "Subject"      | head -n 1 | sed -r 's/Subject:.*v([0-9]{1,}).*/\1/'`
	CURRENT=`cat ${COVER_FILE}    | grep "Subject"      | head -n 1 | sed -r 's/Subject: \[PATCH.*([0-9]{1,})\/([0-9]{1,})\] (.*)/\1/'`
	TOTAL=`cat ${COVER_FILE}      | grep "Subject"      | head -n 1 | sed -r 's/Subject: \[PATCH.*([0-9]{1,})\/([0-9]{1,})\] (.*)/\2/'`
	if [ ${#VERSION} -gt 10 ]; then
		VERSION="1"
	fi
	if [ ${#CURRENT} -gt 10 ]; then
		CURRENT=""
	fi
	if [ ${#TOTAL} -gt 10 ]; then
		TOTAL=""
	fi



	DATE_STR=`cat ${COVER_FILE}   | grep "Date"	    | head -n 1 | sed -r 's/Date: (.*) [-|+]([0-9]{1,}).*/\1/'`
	DATE_VALUE=`date -d "${DATE_STR}" +%s`
	DATE=`date -d @${DATE_VALUE}  "+%Y/%m/%d"`

	AUTHOR=`cat ${COVER_FILE}     | grep "From:"        | head -n 1 | sed -r 's/From: (.*) <(.*)>/\1/'`
	EMAIL=`cat ${COVER_FILE}      | grep "From:"        | head -n 1 | sed -r 's/From: (.*) <(.*)>/\2/'`

	MESSAGE_ID=`cat ${COVER_FILE} | grep "Message-Id: " | head -n 1 | sed -r 's/Message-Id: <(.*)>/\1/'`
	WEB_URL=https://lore.kernel.org/all/${MESSAGE_ID}
	LIST_ARCHIVE_URL=${WEB_URL}

	echo "---"
	echo "| 时间  | 作者 | 特性 | 描述 | 是否合入主线 | 链接 |" | tee ${MESSAGE_ID}.md
	echo "|:-----:|:----:|:----:|:----:|:------------:|:----:|" | tee -a ${MESSAGE_ID}.md
	if [ x"${TOTAL}" = x ]; then
		echo "| ${DATE} | ${AUTHOR} <${EMAIL}> | [${SUBJECT}](${WEB_URL}) | ${ID} | v${VERSION} ☐☑✓ | [LORE](${LIST_ARCHIVE_URL}) |" | tee -a ${MESSAGE_ID}.md
	else
		echo "| ${DATE} | ${AUTHOR} <${EMAIL}> | [${SUBJECT}](${WEB_URL}) | ${ID} | v${VERSION} ☐☑✓ | [LORE v${VERSION},0/${TOTAL}](${LIST_ARCHIVE_URL}) |" | tee -a ${MESSAGE_ID}.md
	fi
}

main()
{
	local ID=$1

	mkdir -p ${ID}
	cd ${ID}
	b4 am ${ID}

	COVER_FILE=`ls *.cover`
	if [ $? -ne 0 ]; then
		# Not a patchset, find the mbox file
		COVER_FILE=`ls *.mbx`
	fi

	get_series_from_file ${COVER_FILE}
}

main $1
