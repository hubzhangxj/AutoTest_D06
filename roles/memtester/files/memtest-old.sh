#!/bin/bash
set -x
run_memtester()
{
	# $1难道是配置满内存后，获取的内存大小，后面用作判断比较;
    #memory_size=$1
	#获取总内存大小
    total_memory=$(free -m | grep 'Mem' | awk '{print $2}')

    if [ $? -ne 0 ]; then
        echo 'read the total memory failed'
        return -1
    fi

#    if [ $total_memory -le $memory_size ]; then
#        echo 'can not recognize all the DIMM chips'
#        echo "Can find the total memory is $total_memory MB"
#        return -4
#    fi
	
	#获取processor的数目
    thread_num=$(cat /proc/cpuinfo | sed -n '/processor/h; ${ x; p; }' | awk '{print $3}' )
    thread_num=$[ thread_num + 1 ]
	
	#总内存的80%除以线程数，获得每个PROCESSOR的内存大小，最后取整数值
    each_memory=$(awk 'BEGIN{printf '$total_memory'*0.8/'$thread_num'}')
    each_memory=$(echo $each_memory | awk -F '.' '{print $1}')
    if [ $? -ne 0 ]; then
        echo 'compute the valuable for memtester wrong'
        return -2
    fi

    for (( i=1; i<=$thread_num; i++)); do
	{
        #./bin/memtester 3m 1 > result"$i".log
        ./bin/memtester "$each_memory"m 1 1>result"$i".log 2>>fail.log
        if [ $? != 0 ]; then
            echo "running memtester failed $i"
            echo "thread $i is Failed " >> fail.log
            return -3
        fi
        sed -n '1,7p' result"$i".log
        if [ $? != 0 ]; then
            echo 'can not print the log file'
            echo 'the failure info is '$(echo result${i}.log) >> fail.log
        fi
        free_memory=$(free -m | grep 'Mem' | awk '{print $2}')
        echo "the available memory is $free_memory MB, the $i process has finished"
        result=$(cat result"$i".log | grep 'FAILURE')
        if [ "$result"x != ''x ]; then
            echo 'run the memtester has been wrong'
            echo 'the failure info is '$result
            echo "thread $i is Failed " >> fail.log
            echo $result
            return -3
        fi
	} &
    done
    wait

    echo "++++++++++=memtester finished+++++++++++"

    output=$(find . -name 'fail.log')
    if [ "$output"x != ''x ] && [ x"$(ls -s ./fail.log | awk '{print $1}')" != x"0"  ] ;  then
        echo 'there is wrong with the memory'
        return -4
    else
        echo 'memory test succeed'
        return 0
    fi
}

run_memtester 240000


