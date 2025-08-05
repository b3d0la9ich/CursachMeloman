import { Link } from 'react-router-dom';

export default function Home() {
  return (
    <div style={{ textAlign: 'center', marginTop: 100 }}>
      <h1>База данных меломана</h1>
      <Link to="/login"><button>Войти</button></Link>
      <Link to="/register" style={{ marginLeft: 10 }}><button>Регистрация</button></Link>
    </div>
  );
}
