#!/bin/bash
# check_services.sh

echo "🔍 Checking Airflow Services..."
echo ""

# Check if containers are running
echo "📦 Container Status:"
docker-compose ps

echo ""
echo "🏥 Service Health Checks:"

# Check PostgreSQL
echo -n "PostgreSQL: "
docker-compose exec -T postgres pg_isready -U airflow && echo "✅ HEALTHY" || echo "❌ UNHEALTHY"

# Check Redis
echo -n "Redis: "
docker-compose exec -T redis redis-cli ping | grep -q PONG && echo "✅ HEALTHY" || echo "❌ UNHEALTHY"

# Check Airflow API Server
echo -n "Airflow API: "
curl -s http://localhost:8080/api/v2/monitor/health | grep -q "healthy" && echo "✅ HEALTHY" || echo "❌ UNHEALTHY"

echo ""
echo "🔗 Access URLs:"
echo "   Airflow UI: http://localhost:8080"
echo "   Username: airflow"
echo "   Password: airflow"

echo ""
echo "📊 Database Check:"
docker-compose exec -T postgres psql -U airflow -d airflow -c "\l" | head -n 10