from app import app, db
from models import User, Question, GameResult

# ✅ Используем контекст приложения
with app.app_context():
    # 🛑 Сначала удаляем связанные данные
    db.session.query(GameResult).delete()
    
    # 🛑 Затем удаляем пользователей и вопросы
    db.session.query(User).delete()
    db.session.query(Question).delete()
    
    # ✅ Применяем изменения
    db.session.commit()

print("✅ База данных очищена!")
