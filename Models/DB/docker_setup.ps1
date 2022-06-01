./docker_db_insert_data.ps1

echo "sleep to ensure container startup has completed"
Start-Sleep -s 7

echo "run db setup python file"

python ../../setup_db.py

echo "successfully ran db setup"

echo "entering container and inserting file located in dumps folder"
docker exec -u root -it testdb bash -c "mysql --password=123 testdb < /home/dumps/*.sql"

