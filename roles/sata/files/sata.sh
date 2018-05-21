#!/bin/bash
 
SATA=$(fdisk -l | grep '.*GiB' | awk '{if($3 > 200.0){print}}'| awk '{print $2}')

if [ x"$SATA" = x"" ]; then
    SATA=$(fdisk -l | grep '.*TiB' | awk '{print $2}')
fi

SATA_NAME=${SATA//:/ }
SATA_NAME='/dev/sdb'
echo $SATA_NAME
read -a WORDS <<< $SATA_NAME


#if [ "${#WORDS[*]}" -ne 12 ]; then
#    echo "can not recognize all the disk"
#    echo "can only recgnize ${#WORDS[*]} disks"
#    blkid
#    exit -1
#fi

declare -a SATA_DEV

for i in ${WORDS[*]} ; do
{
    SATA_DEV=$(fdisk -l | grep $i'[0-9]'| awk '{print $1}')
    if [ x"$SATA_DEV" = x"" ]; then
        SATA_DEV=$(fdisk -l | grep $i| awk '{print $1}')
    fi
    flag=0
    
    # mount, read, write and umount the SATA one by one.
    for k in ${SATA_DEV[*]}
    do 
        echo "----------$k---------------"
        MOUNT_NAME=${k/dev/mnt}
     
        mounted_sata=$( mount | grep -w "$MOUNT_NAME")
        # if mount_name=/mnt/sdb1 not be mounted     
        if [ "$mounted_sata"x != ""x ]; then
            umount $MOUNT_NAME
        fi
        if [ -d $MOUNT_NAME ]; then
            rm -fr $MOUNT_NAME
        fi  
        #creare mount_name=/mnt/sdb1 and mount it,
        mkdir -p $MOUNT_NAME && mount $k $MOUNT_NAME 
   
        if [ $? -ne 0  ]; then
            echo "mount $k to $MOUNT_NAME FAILED"
            flag=1
        fi  

        OUTPUT=$(df -k | grep $MOUNT_NAME)
        if [ ${#OUTPUT} -eq 0 ]; then
            echo "mount $MOUNT_NAME FAILED"
            flag=1
        fi  

        FILE_NAME='300.ltp.tar'
        echo  "----`pwd`-----"
        #cp './d05_scripts/'$FILE_NAME ./
        if [ -f "$FILE_NAME" ]; then
            md5_pre=$(md5sum $FILE_NAME)
                md5_pre=$(echo $md5_pre | awk '{print $1}')
            cp $FILE_NAME $MOUNT_NAME
            rm -fr $FILE_NAME
            cp $MOUNT_NAME'/'$FILE_NAME ./
            if [ $? -ne 0 ]; then
                echo "read and write FAILED"
                flag=1
            fi

            md5_after=$(md5sum $FILE_NAME)
                md5_after=$(echo $md5_after | awk '{print $1}')
            if [ "$md5_pre"x != "$md5_after"x ]; then
                echo 'read error'
                flag=1
            fi
            
            rm -fr $MOUNT_NAME'/'$FILE_NAME
            if [ $? -ne 0 ]; then
                echo "TEST FAILED"
                flag=1
            fi
        else
            echo "the test file is not exists"
                flag=1
        fi
            
        umount $MOUNT_NAME
        if [ $? -ne 0 ]; then
            echo "umount $MOUNT_NAME failed"
            flag=1
        fi
        rm -fr $MOUNT_NAME
        if [ $? -ne 0 ]; then
            echo "umount failed"
            flag=1
       fi
    uuid=$(echo `blkid -s UUID $k` | awk '{print $2}' | sed 's/UUID=\"//g' | sed 's/\"//g')
    if [ $flag -eq 0 ]; then
        echo "The sata disk $uuid works pass"
    else
        echo "The sata disk $uuid works fail"
    fi

    done

}
done 

echo "SATA test succeed"
exit 0




