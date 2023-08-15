#!/bin/bash
 


INSTR="0"
START_INSTR="$2"
if [[ "$START_INSTR" == "" ]]; then
    START_INSTR="0"
fi

export ONLY="$3"

F_Exec () {
    INSTR="$((INSTR+1))"
    [ "$INSTR" -le "$((START_INSTR-1))" ] && return

    ERR="F"
    ER=""
    COMM="$@"
    printf "\n\n========================================================================================\n"
    eval $@
    CODE=$?
    [ $CODE -ne 0 ] && ERR="T"
    printf "========================================================================================\n"
    printf "$COMM"
    [ "$ERR" == "T" ] && printf "      ERROR! ($CODE)    Instruction: $INSTR;    Continue? (y/n)\n"
    [ "$ERR" == "F" ] && printf "      OK!       Instruction: $INSTR;     Continue? (y/n)\n"

    [ "$ONLY" == "only" ] && exit 0
    read -n 1 CH
    [ "$CH" == "n" ] && exit 1

}
export -f F_Exec




# Display
if [[ "$1" == "docs" || "$1" == "all" ]]; then

    F_Exec /usr/bin/feedex --version
    F_Exec /usr/bin/feedex --about
    F_Exec /usr/bin/feedex -h
    F_Exec /usr/bin/feedex -hh

    F_Exec /usr/bin/feedex --help-query
    F_Exec /usr/bin/feedex --help-feeds
    F_Exec /usr/bin/feedex --help-entries
    F_Exec /usr/bin/feedex --help-rules
    F_Exec /usr/bin/feedex --help-scripting
    F_Exec /usr/bin/feedex --help-examples

fi


if [[ "$1" == "db" || "$1" == "all" ]]; then
    # Test params and db edits

    TEST_DB="test.db"
    [ -d "$TEST_DB" ] && rm -r "$TEST_DB"
    
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --defaults --default-feeds --create-db

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --lock-db
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --unlock-db
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --db-stats
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --lock-db
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --db-stats
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --unlock-db

    export FEEDEX_DB_PATH="test2.DB"
    [ -d "$FEEDEX_DB_PATH" ] && rm -r "$FEEDEX_DB_PATH"
    F_Exec /usr/bin/feedex --debug --defaults --default-feeds --create-db

    F_Exec /usr/bin/feedex --debug --lock-db
    F_Exec /usr/bin/feedex --debug --db-stats
    F_Exec /usr/bin/feedex --debug --unlock-db

    F_Exec /usr/bin/feedex --debug --db-maintenance

    unset FEEDEX_DB_PATH

fi



if [[ "$1" == "config" || "$1" == "all" ]]; then

    TEST_CONFIG="cli_test1.conf"
    F_Exec /usr/bin/feedex --config="$TEST_CONFIG" --db-stats

    TEST_CONFIG="cli_test_qr.conf"
    F_Exec /usr/bin/feedex --config="$TEST_CONFIG" --db-stats

    TEST_CONFIG="cli_test1.conf"
    F_Exec /usr/bin/feedex --config="$TEST_CONFIG"  --db-stats

fi



if [[ "$1" == "db_special" || "$1" == "all" ]]; then

    export TEST_DB="test_full_copy.db"
    [[ -d "test_full_copy.db" ]] && rm -r "test_full_copy.db" 
    cp -r "test_full.db" "test_full_copy.db"

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --delete-feed 42
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --delete-feed 43
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --delete-feed 44
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --delete-feed 45

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --mark 4 1
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --mark 5 1

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --delete-entry 4
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --delete-entry 5
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --delete-entry 6
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --delete-entry 7
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --delete-entry 8

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --empty-trash
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --clear-history

fi

if [[ "$1" == "notify" || "$1" == "all" ]]; then
#28
    export FEEDEX_DB_PATH="test_full.db"

    F_Exec /usr/bin/feedex --debug -g

    F_Exec /usr/bin/feedex --debug --location='\*London\*' -q
    F_Exec /usr/bin/feedex --debug --location=USA -q
    F_Exec /usr/bin/feedex --debug --location=USA -q russia
 
    F_Exec /usr/bin/feedex --debug --last -q
    F_Exec /usr/bin/feedex --debug --last_week -R
    F_Exec /usr/bin/feedex --debug --last_week --group=feed --depth=10 -R
    F_Exec /usr/bin/feedex --last_week --trending
    F_Exec /usr/bin/feedex --last_n=2 --group=category -q
    F_Exec /usr/bin/feedex --last_n=2 --headlines --group=category -q
    F_Exec /usr/bin/feedex --last_n=2 --long --group=category -q
    F_Exec /usr/bin/feedex --last_n=2 --group=category -q
    F_Exec /usr/bin/feedex --last --last_n=-2 -q
    F_Exec /usr/bin/feedex --last_n=sssssss -q
    F_Exec /usr/bin/feedex --last --group=flag --depth=3 -q
    F_Exec /usr/bin/feedex --last --headlines --group=flag --depth=3 -q
    F_Exec /usr/bin/feedex --headlines --group=category --depth=5 --last_n=3 -q
    F_Exec /usr/bin/feedex --group=feed --depth=5 --last_n=3 -q
    F_Exec /usr/bin/feedex --headlines --group=feed --depth=5 --last_n=3 -q
    F_Exec /usr/bin/feedex --headlines --group=similar --depth=5 --last_n=1 -q
    F_Exec /usr/bin/feedex --csv --last_n=3 -q
    F_Exec /usr/bin/feedex --json --last_n=3 -q
    F_Exec /usr/bin/feedex --export --last_n=3 -q
    F_Exec /usr/bin/feedex --long --last_n=3 -q
    F_Exec /usr/bin/feedex --group=category --last_n=3 -q
    F_Exec /usr/bin/feedex --group=daily --last_n=3 -q
    F_Exec /usr/bin/feedex --group=hourly --last_n=3 -q

   unset FEEDEX_DB_PATH

fi





if [[ "$1" == "basic_queries" || "$1" == "all" ]]; then
# Basic queries

    export FEEDEX_DB_PATH="test_full.db"
 
    F_Exec /usr/bin/feedex -r 121
    F_Exec /usr/bin/feedex --summarize=90 -r 121
    F_Exec /usr/bin/feedex -r 11
    F_Exec /usr/bin/feedex -L
    F_Exec /usr/bin/feedex --list-categories
    F_Exec /usr/bin/feedex --list-feeds-cats
    F_Exec /usr/bin/feedex --list-learned-terms
    F_Exec /usr/bin/feedex -F 8
    F_Exec /usr/bin/feedex -F 1111111
    F_Exec /usr/bin/feedex --examine-feed 8
    F_Exec /usr/bin/feedex --examine-feed 1111111111
    F_Exec /usr/bin/feedex -C Science
    F_Exec /usr/bin/feedex --csv -C Science
    F_Exec /usr/bin/feedex --json -C Travel
    F_Exec /usr/bin/feedex --list-history
    F_Exec /usr/bin/feedex --list-rules
    F_Exec /usr/bin/feedex --long --list-rules
    F_Exec /usr/bin/feedex --list-flags
    F_Exec /usr/bin/feedex --feed=8 --flag=1 -q ''
    F_Exec /usr/bin/feedex --flag=all_flags --last_quarter -q ''
    F_Exec /usr/bin/feedex --flag="Important!" --last_quarter -q ''

    F_Exec /usr/bin/feedex --last --trends
    F_Exec /usr/bin/feedex --last --trending

    F_Exec /usr/bin/feedex --list-fetches
    F_Exec /usr/bin/feedex --long --list-fetches


    unset FEEDEX_DB_PATH
    
fi


if [[ "$1" == 'queries' || "$1" == "all" ]]; then


    export FEEDEX_DB_PATH="test_full.db"
 
    F_Exec /usr/bin/feedex --debug --last_quarter --group=daily --plot --rel-in-time 155
    F_Exec /usr/bin/feedex --debug --last_quarter --group=daily --plot --rel-in-time 145

    F_Exec /usr/bin/feedex --debug --feed=8 --last -q ''
    F_Exec /usr/bin/feedex --debug --feed=8 --last -q ''
    F_Exec /usr/bin/feedex --debug --feed=8 --last_week -q ""
    F_Exec /usr/bin/feedex --debug --category=Technology --last_week -q ""
    F_Exec /usr/bin/feedex --field=author --last_month -q "John"
    F_Exec /usr/bin/feedex --debug --field=category --last_month -q "IT"

    F_Exec /usr/bin/feedex --debug --type=string --feed=8 --last -q ''
    F_Exec /usr/bin/feedex --type=string --debug --feed=8 --last -q ''
    F_Exec /usr/bin/feedex --type=string --debug --feed=8 --last_week -q ''
    F_Exec /usr/bin/feedex --type=string --field=author --last_month -q "John"
    F_Exec /usr/bin/feedex --type=string --debug --field=publisher --last_month -q "Ars"

    F_Exec /usr/bin/feedex --debug --type=full --feed=8 --last -q ''
    F_Exec /usr/bin/feedex --type=full --debug --feed=8 --last -q ''
    F_Exec /usr/bin/feedex --type=full --debug --feed=8 --last_week -q ''
    F_Exec /usr/bin/feedex --type=full --field=author --last_month -q "John"
    F_Exec /usr/bin/feedex --type=full --debug --field=publisher --last_month -q "Ars"
    F_Exec /usr/bin/feedex --type=full --field=title --last_month -q "Does"
    F_Exec /usr/bin/feedex --type=full --last_quarter -q "Vaccinations"

    F_Exec /usr/bin/feedex --debug --term-net "vaccine"
    F_Exec /usr/bin/feedex --debug --type=full --feed=8 --last_quarter --context "vaccine"
    F_Exec /usr/bin/feedex --debug --type=string --feed=8 --last_quarter --context "vaccine"
    F_Exec /usr/bin/feedex --debug --feed=8 --last_quarter --context "vaccine"

    F_Exec /usr/bin/feedex --debug --type=full --feed=8 --last_month --group=daily --time-series "vaccine"
    F_Exec /usr/bin/feedex --debug --type=full --feed=8 --last_month --group=daily --plot --time-series "Biden vaccine"

   unset FEEDEX_DB_PATH

fi


if [[ "$1" == 'queries_wildcards' || "$1" == "all" ]]; then

    export FEEDEX_DB_PATH="test_full.db"

    F_Exec /usr/bin/feedex --type=fts --case_ins --from='2021-01-01' --to='2021-06-01' -q "does"
    F_Exec /usr/bin/feedex --type=fts --case_ins --from='202ssssssss1-01-01' --to='2021-06-01' -q "Does"
    F_Exec /usr/bin/feedex --type=fts --case_ins --from='2021-01-01' --to='202aaaaaaaa1-06-01' -q "Does"

    F_Exec /usr/bin/feedex --type=fts --case_ins --last_month -q "Does"
    F_Exec /usr/bin/feedex --type=fts --case_sens --last_month -q "Does"
    F_Exec /usr/bin/feedex --type=string --case_ins --last_month -q "Does"
    F_Exec /usr/bin/feedex --type=string --case_sens --last_month -q "Does"
    
    F_Exec /usr/bin/feedex --debug --type=fts --feed=8 --last_quarter --context "'vaccine expected'"
    F_Exec /usr/bin/feedex --debug --type=string --feed=8 --last_quarter --context "'vaccine * expected'"
    F_Exec /usr/bin/feedex --debug --feed=8 --last_quarter --context "'vaccine Expected'"

    F_Exec /usr/bin/feedex --debug --type=full --feed=8 --last_month --group=daily --plot --time-series "'Vaccine expected'"
    F_Exec /usr/bin/feedex --debug --type=string --feed=8 --last_month --group=daily --plot --time-series "'vaccine \* expected'"

   unset FEEDEX_DB_PATH


fi

if [[ "$1" == 'queries_special' || "$1" == "all" ]]; then

    export FEEDEX_DB_PATH="test_full.db"

    F_Exec /usr/bin/feedex -r 88
    F_Exec /usr/bin/feedex --details -r 88157777777777
    F_Exec /usr/bin/feedex --details -r 1466
    F_Exec /usr/bin/feedex --last_week -S 88157777777777
    F_Exec /usr/bin/feedex --debug --last_week -S 88157
    F_Exec /usr/bin/feedex -r 881
    F_Exec /usr/bin/feedex --debug -r 881
#118
    unset FEEDEX_DB_PATH

fi



# DB Actions
if [[ "$1" == 'actions_feed' || "$1" == "all" ]]; then
    
    TEST_DB="test.db"
    [ -d "$TEST_DB" ] && rm -r "$TEST_DB"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --defaults --default-feeds --create-db

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --delete-feed 1111111
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --delete-feed 1
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" -L
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --restore-feed 111111111
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --restore-feed 1
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" -L
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-feed 1 autoupdate 0
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-feed 1 autoupdate 1
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-feed 1 category Notes
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-feed 1 category "<NONE>"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-feed 1 parent_id Hilight
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" -L
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-feed 1 parent_id "<NONE>"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-feed 1 handler "<NONE>"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-feed 1 handler http
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-feed 1 handler rsssss
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-feed 1 handler rss
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-feed 1 interval 14000
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" -L
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-feed 1 error 5
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-feed 1 error 0
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" -L
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-feed 1 link ad7t183gbklladbfkjahfskjhfash
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-feed 1 autoupdate sssssss
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-feed 1 parent_id Hilight
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" -L
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-feed 1 parent_id "<NULL>"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" -L
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-feed 1 parent_id "<NULL>"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" -L
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-feed 1 auth detect
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --debug -L
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" -L
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --examine-feed 1
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --debug --examine-feed 1
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-feed 1 auth "<NONE>"
#155

fi



if [[ "$1" == 'actions_category' || "$1" == "all" ]]; then

    TEST_DB="test.db"
    [ -d "$TEST_DB" ] && rm -r "$TEST_DB"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --defaults --default-feeds --create-db

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --add-category "'test test'" "test"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --category=Notes --add-category "'test test'" "test"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --list-categories
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --delete-category 111111111111111
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --delete-category "'test test'"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --list-categories
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --restore-category "'test test'"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --list-categories
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-category 11111111 "title" "test111111"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-category "'test test'" "title" "test111111"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --list-categories
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" -C "'test test'"

fi



if [[ "$1" == 'actions_rule' || "$1" == "all" ]]; then

    TEST_DB="test.db"
    [ -d "$TEST_DB" ] && rm -r "$TEST_DB"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --defaults --default-feeds --create-db

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --add-rule "''"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --add-rule "test"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --category=Hilights --add-rule "test"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --feed=8 --add-rule "test1"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --weight=1000 --add-rule "test2"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --weight=1000 --field=author --category=Notes --flag=2 --add-rule "test3"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-rule 1 feed_id 3 

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-rule 1 feed_id 2
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --list-rules
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-rule 1 feed_id 3 
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --list-rules
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-rule 1 field desc
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --list-rules
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-rule 1 field '<NONE>'
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --list-rules
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-rule 1 flag 1
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-rule 1 flag '<NONE>'
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --list-rules

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --feed=1 --add-rule "test"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --field=author --add-rule "test"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --case_ins --feed=1 --add-rule "test"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --case_sens --feed=1 --add-rule "test"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --list-rules
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --add-regex "''"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --add-regex "'[]..\.*aaaa\sd9(][\]][\]]'"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --add-regex "test"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --list-rules
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --add-stemmed "test"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --list-rules
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-rule 1 string 'gfgfgfgf'
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --list-rules
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --delete-rule 1
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --list-rules


fi


if [[ "$1" == 'actions_entry' || "$1" == "all" ]]; then

    export FEEDEX_DB_PATH="test_full.db"

    F_Exec /usr/bin/feedex -r 881579999000000
    F_Exec /usr/bin/feedex -r 157
    F_Exec /usr/bin/feedex --debug --mark 157 0
    F_Exec /usr/bin/feedex --debug -o 157
    F_Exec /usr/bin/feedex --debug --mark 157 0
    F_Exec /usr/bin/feedex --debug --mark 157 1
    F_Exec /usr/bin/feedex --debug --unmark 88157
    F_Exec /usr/bin/feedex --debug --flag 157 2
    F_Exec /usr/bin/feedex --debug --flag 157 0
    F_Exec /usr/bin/feedex --debug --flag 881579999999999 0
    F_Exec /usr/bin/feedex --debug -r 157
    F_Exec /usr/bin/feedex --debug -o 881577777777
    F_Exec /usr/bin/feedex --debug --feed=8 --add-entry "test" "test test test"
    F_Exec /usr/bin/feedex --debug -F 8
    F_Exec /usr/bin/feedex --debug --feed=8 --add-entry "test" "test test test"

    unset FEEDEX_DB_PATH
fi



if [[ "$1" == 'actions_flag' || "$1" == "all" ]]; then

    TEST_DB="test.db"
    [ -d "$TEST_DB" ] && rm -r "$TEST_DB"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --defaults --default-feeds --create-db

    F_Exec /usr/bin/feedex --database="$TEST_DB" --list-flags
    F_Exec /usr/bin/feedex --database="$TEST_DB" --add-flag "test" "test test"
    F_Exec /usr/bin/feedex --database="$TEST_DB" --edit-flag 1 "color_cli" "blue"
    F_Exec /usr/bin/feedex --database="$TEST_DB" --edit-flag 1 "color_cli" "RED"
    F_Exec /usr/bin/feedex --database="$TEST_DB" --list-flags
    F_Exec /usr/bin/feedex --database="$TEST_DB" --edit-flag 1 "id" 2
    F_Exec /usr/bin/feedex --database="$TEST_DB" --edit-flag 1 "id" 333
    F_Exec /usr/bin/feedex --database="$TEST_DB" --list-flags
    F_Exec /usr/bin/feedex --database="$TEST_DB" --delete-flag 2
    F_Exec /usr/bin/feedex --database="$TEST_DB" --list-flags


fi



if [[ "$1" == 'actions_entry_add' || "$1" == "all" ]]; then
    
    TEST_DB="test.db"
    IFILE="test_ifile.json"
    IFILE2="test_ifile2.json"
    IFILE3="test_ifile_long3.json"
    [ -d "$TEST_DB" ] && rm -r "$TEST_DB"
    /usr/bin/feedex --debug --database="$TEST_DB" --defaults --default-feeds --create-db


    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --add-entry "'Test'" "'DESC Test'"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --feed=1 --add-entry "'Test'" "'DESC Test'"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --feed=1 --weight=300 --add-entry "'Test'" "'DESC Test'"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --feed=17777 --add-entry "'Test'" "'DESC Test'"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --feed=sssss --add-entry "'Test'" "'DESC Test'"

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --category='Hilight' --add-entry "'Test'" "'DESC Test'"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --category='Hilight' --no-learn --add-entry "'Test'" "'DESC Test'"

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --feed=1 --add-entry "'Test'" "'DESC Test'" 
    F_Exec /usr/bin/feedex --database="$TEST_DB" -F 1

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --delete-entry 1
    F_Exec /usr/bin/feedex --database="$TEST_DB" -F 1

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --restore-entry 1
    F_Exec /usr/bin/feedex --database="$TEST_DB" -F 1

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --delete-entry 1
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --delete-entry 1
    F_Exec /usr/bin/feedex --database="$TEST_DB" -F 1

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --delete-entry 199999999999
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --restore-entry 199999999999
 

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --category='Notes' --add-entry "'Test'" "'DESC Test'" 
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --category='Notes' --add-entry "'Test'" "'DESC Test'" 

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --import-entries-from-file "$IFILE"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --import-entries-from-file "$IFILE2"

    F_Exec /usr/bin/feedex --database="$TEST_DB" --last_quarter --export --ofile="$IFILE3" --read -q
    
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --import-entries-from-file "$IFILE3"

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --no-learn --import-entries-from-file "$IFILE"

    F_Exec /usr/bin/feedex --database="$TEST_DB" -F 1
    F_Exec /usr/bin/feedex --database="$TEST_DB" -C 'Notes'

    F_Exec /usr/bin/feedex --database="$TEST_DB" -r 2
    F_Exec /usr/bin/feedex --database="$TEST_DB" -r 3

fi


if [[ "$1" == 'actions_migrate' || "$1" == "all" ]]; then
    
    TEST_DB="test_skel.db"
    IFILE="skel_feeds_imp.json"
    IFILE2="skel_flags_imp.json"
    IFILE3="skel_rules_imp.json"
    IFILE4="skel_entries_short_imp.json"
    IFILE5="skel_entries_imp.json"
    [ -d "$TEST_DB" ] && rm -r "$TEST_DB"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --create-db

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --import-feeds "$IFILE"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" -L

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --import-flags "$IFILE2"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --list-flags

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --import-rules "$IFILE3"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --list-rules

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --import-entries-from-file "$IFILE4"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --import-entries-from-file "$IFILE5"

fi






if [[ "$1" == 'actions_entry_edit' || "$1" == "all" ]]; then

    TEST_DB="test.db"
    IFILE="test_ifile.json"
    IFILE2="test_ifile2.json"
    [ -d "$TEST_DB" ] && rm -r "$TEST_DB"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --defaults --default-feeds --create-db

    F_Exec /usr/bin/feedex --database="$TEST_DB" --import-entries-from-file "$IFILE"
    F_Exec /usr/bin/feedex --database="$TEST_DB" -F 1

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-entry 1 text "'Testing editing asssssssss fdfdlfjirjirf fdkjfdkjfksd dsf;j;fkjrijsd;fj;l sd;flj;ljsdf'"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-entry 1 text "'Testing editing asssssssss fdfdlfjirjirf fdkjfdkjfksd dsf;j;fkjrijsd;fj;l sd;flj;ljsdf'"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-entry 1 desc "'Testing editing asssssssss fdfdlfjirjirf fdkjfdkjfksd dsf;j;fkjrijsd;fj;l sd;flj;ljsdf'"

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-entry 1 read 5
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-entry 1 read 0
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" -r 1
    F_Exec /usr/bin/feedex --database="$TEST_DB" -r 1

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-entry 1 flag 5
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-entry 1 flag 0
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" -r 1
    F_Exec /usr/bin/feedex --database="$TEST_DB" -r 1

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-entry 1 feed_id 1
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-entry 1 feed_id 2
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" -r 1
    F_Exec /usr/bin/feedex --database="$TEST_DB" -r 1

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-entry 1 feed_id Notes
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-entry 1 feed_id '<NONE>'
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --edit-entry 1 feed_id 2
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" -r 1
    F_Exec /usr/bin/feedex --database="$TEST_DB" -r 1

    F_Exec /usr/bin/feedex --database="$TEST_DB" --debug --no-learn --parent_category=Hilight --add-entry "test" "test"

fi


if [[ "$1" == 'ling' || "$1" == "all" ]]; then

    TEST_DB="test.db"
    IFILE="test_ifile_ling.json"
    [ -d "$TEST_DB" ] && rm -r "$TEST_DB"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --defaults --default-feeds --create-db

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --import-entries-from-file "$IFILE"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" -r 1
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" -r 2
    F_Exec /usr/bin/feedex --database="$TEST_DB" -r 3
    F_Exec /usr/bin/feedex --database="$TEST_DB" -r 4
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" -r 1
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" -r 2
    

fi



if [[ "$1" == 'actions_fetching' || "$1" == "all" ]]; then

    TEST_DB="test.db"
    [ -d "$TEST_DB" ] && rm -r "$TEST_DB"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --defaults --default-feeds --create-db
    export FEEDEX_DB_PATH="$TEST_DB"

    F_Exec /usr/bin/feedex --debug --add-regex "'[]..\.*aaaa\sd9(][\]][\]]'"

    F_Exec /usr/bin/feedex --debug -L
    F_Exec /usr/bin/feedex --debug -g 1
    F_Exec /usr/bin/feedex --debug -c 2
    F_Exec /usr/bin/feedex --debug -c
    F_Exec /usr/bin/feedex --debug -g
    F_Exec /usr/bin/feedex --debug -u 3
    F_Exec /usr/bin/feedex --debug -u

    F_Exec /usr/bin/feedex --depth=5 --desktop --last -q
    F_Exec /usr/bin/feedex --group=category --depth=5 --desktop --last -q
    F_Exec /usr/bin/feedex --group=flag --depth=5 --desktop --last -q

    F_Exec /usr/bin/feedex --debug -o 1

    F_Exec /usr/bin/feedex --debug --reindex 1
    F_Exec /usr/bin/feedex --debug --relearn 1
    F_Exec /usr/bin/feedex --debug --rerank 2

    F_Exec /usr/bin/feedex --debug --reindex '0..'
    F_Exec /usr/bin/feedex --debug --relearn '..'
    F_Exec /usr/bin/feedex --debug --rerank '..'

    F_Exec /usr/bin/feedex --last -q ''

    F_Exec /usr/bin/feedex -r 1
    F_Exec /usr/bin/feedex -r 2
    F_Exec /usr/bin/feedex -r 30
    F_Exec /usr/bin/feedex -r 4
    F_Exec /usr/bin/feedex -r 5
    F_Exec /usr/bin/feedex -r 6


    unset FEEDEX_DB_PATH
fi




if [[ "$1" == 'actions_port' || "$1" == "all" ]]; then

    FEEDS_EXP="exp_feeds_tst.json"
    RULES_EXP="exp_rules_tst.json"
    FLAGS_EXP="exp_flags_tst.json"
    TEST_DB="test.db"
    TEST_DB_FULL="test_full.db"
    [ -d "$TEST_DB" ] && rm -r "$TEST_DB"
    [ -f "$FEEDS_EXP" ] && rm "$FEEDS_EXP"
    [ -f "$RULES_EXP" ] && rm "$RULES_EXP"
    [ -f "$FLAGS_EXP" ] && rm "$FLAGS_EXP"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --create-db

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB_FULL" --export-feeds "$FEEDS_EXP"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB_FULL" --export-rules "$RULES_EXP"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB_FULL" --export-flags "$FLAGS_EXP"

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --import-feeds "$FEEDS_EXP"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --import-rules "$RULES_EXP"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --import-flags "$FLAGS_EXP"

    F_Exec /usr/bin/feedex --database="$TEST_DB" -L
    F_Exec /usr/bin/feedex --database="$TEST_DB" --list-rules
    F_Exec /usr/bin/feedex --database="$TEST_DB" --list-flags


    F_Exec /usr/bin/feedex --debug --database="$TEST_DB_FULL" --export-feeds "$FEEDS_EXP"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB_FULL" --export-rules "$RULES_EXP"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB_FULL" --export-flags "$FLAGS_EXP"

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --import-feeds "ssssss$FEEDS_EXP"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --import-rules "ssssss$RULES_EXP"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --import-flags "ssssss$FLAGS_EXP"

fi

if [[ "$1" == 'actions_add_from_url' || "$1" == "all" ]]; then

    TEST_DB="test.db"
    [ -d "$TEST_DB" ] && rm -r "$TEST_DB"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --defaults --default-feeds --create-db

    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --add-feed 'http://feeds.arstechnica.com/arstechnica/index'
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --add-feed 'https://www.space.com/feeds/all'
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --no-fetch --add-feed 'https://www.theverge.com/rss/index.xml'
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --handler=local --add-feed 'https://www.siliconvalley.com/feed/'


    F_Exec /usr/bin/feedex --database="$TEST_DB" -L

fi


if [[ "$1" == 'catalog' || "$1" == "all" ]]; then

    TEST_DB="test.db"
    [ -d "$TEST_DB" ] && rm -r "$TEST_DB"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --create-db

    F_Exec /usr/bin/feedex --database="$TEST_DB" -qc
    F_Exec /usr/bin/feedex --database="$TEST_DB" -qc london
    F_Exec /usr/bin/feedex --database="$TEST_DB" --field=location -qc london
    F_Exec /usr/bin/feedex --database="$TEST_DB" --category=Science -qc
    F_Exec /usr/bin/feedex --database="$TEST_DB" --category=Science -qc science

    F_Exec /usr/bin/feedex --database="$TEST_DB" --import-from-catalog "4085, 4066, 3648, 3509, 3430, 3192, 3087"
    F_Exec /usr/bin/feedex --database="$TEST_DB" --list-feeds-cats


fi




if [[ "$1" == "gui" ]]; then

    TEST_DB="test_full.db"
    [ -f "$TEST_DB" ] && rm "$TEST_DB"
    F_Exec /usr/bin/feedex --debug --database="$TEST_DB" --gui

fi
if [[ "$1" == "gui_clean" ]]; then

    TEST_DB="test_gui.db"
    [ -f "$TEST_DB" ] && rm "$TEST_DB"

    F_Exec /usr/bin/feedex --database="$TEST_DB" --gui

fi