/*

import axios from 'axios';

export const login = async (email, password) => {
  const response = await axios.post('http://TU_BACKEND/api/login', {
    email,
    password,
  });

  return response.data; 
};
*/

export const login = (email, password) => {
    // Lógica de login (puede ser una llamada a tu API)
    return new Promise((resolve, reject) => {
      if (email === 'test@domain.com' && password === '12345') {
        resolve()
      } else {
        reject('Credenciales incorrectas')
      }
    })
  }
  
  export const register = (email, password) => {
    // Lógica de registro (puede ser una llamada a tu API)
    return new Promise((resolve) => {
      console.log('Usuario registrado:', email)
      resolve()
    })
  }