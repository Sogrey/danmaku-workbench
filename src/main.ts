import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import './assets/styles/variables.css'
import './assets/styles/base.css'

createApp(App).use(createPinia()).mount('#app')
