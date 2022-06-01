$pass = '123'
$img_port = 3306
$local_port = 3306
$name = 'testdb'
$dbname = 'testdb'

echo 'removing old container and image'
./docker_db_shutdown.ps1

echo 'builder container and image and moving dump to container'
docker build -t bachapp:latest .

$img = "bachapp:latest"


echo 'starting container'
docker run --detach `
	--name testdb -e MARIADB_PASSWORD=$pass `
	-e MARIADB_ROOT_PASSWORD=$pass `
	-e MARIADB_DATABASE=$name `
	-p ${local_port}:${img_port} `
	$img
