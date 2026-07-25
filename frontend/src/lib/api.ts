import axios from 'axios';
export const api=axios.create({baseURL:'/api/v1'});
api.interceptors.request.use(config=>{const token=localStorage.getItem('ms_token');if(token)config.headers.Authorization=`Bearer ${token}`;return config});
api.interceptors.response.use(r=>r,error=>{if(error.response?.status===401&&localStorage.getItem('ms_token')){localStorage.removeItem('ms_token');localStorage.removeItem('ms_user');window.location.href='/login'}return Promise.reject(error)});
export async function demoLogin(email='admin@infrarelay.local'){const {data}=await api.post('/auth/login',{email});localStorage.setItem('ms_token',data.access_token);localStorage.setItem('ms_user',JSON.stringify(data.user));return data}
