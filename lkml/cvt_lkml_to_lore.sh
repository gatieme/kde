#!/bin/bash

cvt_lkml_to_lore()
{
    tmpfile=$(mktemp ./.cvt_links.XXXXXXX)

    header=$(echo $1 | sed 's@/lkml/@/lkml/headers/@')

    wget -qO - $header > $tmpfile
    if [[ $? == 0 ]] ; then
	link=$(grep -i '^Message-Id:' $tmpfile | head -1 | \
		   sed -r -e 's/^\s*Message-Id:\s*<\s*//' -e  's/\s*>\s*$//' -e 's@^@https://lore.kernel.org/r/@')
	#    echo "testlink: $link"
	if [ -n "$link" ] ; then
	    wget -qO - $link > /dev/null
	    if [[ $? == 0 ]] ; then
		echo $link
	    fi
	fi
    fi

    rm -f $tmpfile
}

cvt_lkml_to_lore_file()
{
	git grep -P -o "\bhttps?://(?:www.)?lkml.org/lkml[\/\w]+" $@ |
		while read line ; do
			echo $line
			file=$(echo $line | cut -f1 -d':')
			link=$(echo $line | cut -f2- -d':')
			newlink=$(cvt_lkml_to_lore $link)
			if [[ -n "$newlink" ]] ; then
				sed -i -e "s#\b$link\b#$newlink#" $file
			fi
		done
}

cvt_lkml_to_lore "$1"
