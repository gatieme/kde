#!/bin/bash

#!/bin/bash
# demo sh batch.sh

PROJECT=$1
YEAR=$2

for month in `seq 1 1 12`
do
	MONTH=`printf "%02d\n" ${month}`
	for day in `seq 1 1 31`
	do
		DAY=`printf "%02d\n" ${day}`
		echo "${YEAR}-${MONTH}-${DAY}"
		sh ./get_patchwork_series.sh -p ${PROJECT} -d ${YEAR}-${MONTH}-${DAY}
	done
done
