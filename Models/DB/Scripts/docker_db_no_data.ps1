$pass = '123'
$img_port = 3306
$local_port = 3306
$name = 'testdb'
$dbname = 'testdb'

$img = "mariadb:latest"


echo 'starting container'

docker run --detach `
	--name testdb -e MARIADB_PASSWORD=$pass `
	-e MARIADB_ROOT_PASSWORD=$pass `
	-e MARIADB_DATABASE=$name `
	-p ${local_port}:${img_port} `
	$img

echo 'sleep to ensure container startup has completed'
Start-Sleep -s 7

echo 'run db setup python file'

python ../../setup_db.py