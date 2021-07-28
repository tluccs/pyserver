
if [ ! -d "logs" ] 
then
    mkdir logs
fi
python GenericServer.py > logs/serv_log.txt &
echo "Started example server!"
sleep .1
python GenericClient.py > logs/C0_log.txt &
echo "Started C0 !"
sleep .1 
python GenericClient.py > logs/C1_log.txt &
echo "Started C1 !"
sleep .1
python GenericClient.py > logs/C2_log.txt &
echo "Started C2 !"
sleep 5
echo "done."