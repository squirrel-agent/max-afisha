import {Onboarding} from './pages/Onboarding';import {Home} from './pages/Home';import {useApp} from './store/app';import './styles.css';import './city-picker.css';
export default function App(){return useApp(s=>s.onboarded)?<Home/>:<Onboarding/>}
