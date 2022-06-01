$container_name="testdb"
$db_name="testdb"
$user_name="root"
$path="./db_dump.sql"
$password="123"

docker exec $container_name mysqldump -p $password $db_name > $path