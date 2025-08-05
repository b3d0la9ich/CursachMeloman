import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const navigate = useNavigate();

  const handleRegister = async () => {
    if (password !== confirm) return alert("Пароли не совпадают");

    try {
      await axios.post('http://localhost:5000/api/register', { email, password });
      alert("Регистрация успешна!");
      navigate('/login');
    } catch (err) {
      alert('Ошибка: ' + (err.response?.data?.message || 'ошибка'));
    }
  };

  return (
    <div>
      <h2>Регистрация</h2>
      <input placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input placeholder="Пароль" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
      <input placeholder="Повторите пароль" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
      <button onClick={handleRegister}>Зарегистрироваться</button>
    </div>
  );
}
