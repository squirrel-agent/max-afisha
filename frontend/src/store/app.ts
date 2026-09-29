import {create} from 'zustand';
import type { CityId } from '../data/cities';

type State={
  userId:string|null;
  city:CityId;
  onboarded:boolean;
  setUser:(id:string)=>void;
  clearUser:()=>void;
  setCity:(city:CityId)=>void;
  resetQuestionnaire:()=>void;
  finish:()=>void;
};
const savedCity=localStorage.getItem('afisha_city');
const initialCity:CityId=savedCity==='saint-petersburg'?'saint-petersburg':'moscow';
export const useApp=create<State>((set)=>({
  userId:localStorage.getItem('afisha_user'),
  city:initialCity,
  // Completion lives only in the current React session so a reload can start a fresh selection.
  onboarded:false,
  setUser:(id)=>{localStorage.setItem('afisha_user',id);set({userId:id})},
  clearUser:()=>{localStorage.removeItem('afisha_user');set({userId:null})},
  setCity:(city)=>{localStorage.setItem('afisha_city',city);set({city})},
  resetQuestionnaire:()=>set({onboarded:false}),
  finish:()=>set({onboarded:true}),
}));
