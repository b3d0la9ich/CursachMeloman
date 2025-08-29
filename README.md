# CursachMeloman

1 docker compose down -v
2 docker compose build
3 docker compose up
4 docker compose exec web bash
flask db migrate -m "init"
flask db upgrade
flask load-catalog