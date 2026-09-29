from __future__ import annotations
import asyncio
import re
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.cities import is_supported_city
from app.ml.encoder import get_text_encoder
from app.models.user import User, UserPreference
from app.models.event import Event
from app.models.interaction import Interaction, SavedEvent

router=APIRouter(prefix='/users',tags=['users'])

WHEN_LABELS = {
    "today_evening": "сегодня вечером",
    "tomorrow": "завтра",
    "weekend": "на ближайших выходных",
}
COMPANY_LABELS = {
    "solo": "один",
    "pair": "вдвоём",
    "small_group": "компания 3–4 человека",
}
VIBE_LABELS = {
    "calm": "спокойно",
    "active": "активно",
    "curious": "познавательно",
    "fun": "весело",
    "romantic": "романтично",
}
DURATION_LABELS = {
    "short": "до 2 часов",
    "medium": "2–4 часа",
    "long": "почти весь день",
}

def _parse_budget_text(value: str | None) -> int | None:
    if not value:
        return None
    normalized = value.lower().replace("\xa0", " ").replace(" ", "")
    matches = list(re.finditer(r"(\d+(?:[.,]\d+)?)\s*(к|k|тыс)?", normalized))
    if not matches:
        return None
    amounts = []
    for match in matches:
        amount = float(match.group(1).replace(",", "."))
        if match.group(2):
            amount *= 1000
        amounts.append(max(0, int(amount)))
    return max(amounts)

def _parse_duration_text(value: str | None) -> tuple[int | None, int | None]:
    if not value:
        return None, None
    normalized = value.lower().replace(",", ".")
    values = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", normalized)]
    if not values:
        return None, None
    multiplier = 60 if re.search(r"час|ч\b|hour", normalized) else 1
    minutes = [max(0, min(1440, int(v * multiplier))) for v in values[:2]]
    if len(minutes) == 1:
        return 0, minutes[0]
    return min(minutes), max(minutes)

def _answer_label(code: str | None, custom: str | None, labels: dict[str, str]) -> str | None:
    if code == "custom":
        return custom.strip() if custom and custom.strip() else None
    return labels.get(code or "", code)

class UserCreate(BaseModel): city:str='moscow'
class CityUpdate(BaseModel): city:str
class Prefs(BaseModel):
 categories:list[str]=Field(default_factory=list); genres:list[str]=Field(default_factory=list); budget_max:int|None=None
 budget:str|None=None; duration:str|None=None
 preferred_period:str|None=None; company:str|None=None; novelty_preference:float=0.5
 # Questionnaire fields are optional to preserve compatibility with the
 # original onboarding payload.  Free-form values are retained separately.
 when:str|None=None; when_text:str|None=None
 company_size:str|None=None; company_text:str|None=None
 vibe:str|None=None; vibe_text:str|None=None
 duration_min:int|None=Field(default=None, ge=0, le=1440)
 duration_max:int|None=Field(default=None, ge=0, le=1440)
 duration_text:str|None=None
 budget_text:str|None=None
 questionnaire_version:str|None=Field(default=None, max_length=32)
class Action(BaseModel):
 event_id:UUID
 action:str
 run_id:UUID|None=None
 position:int|None=Field(default=None, ge=1)
 surface:str|None=None
 algorithm_version:str|None=None

@router.post('')
async def create_user(payload:UserCreate,db:AsyncSession=Depends(get_db)):
 if not is_supported_city(payload.city): raise HTTPException(400,f"Unsupported city: {payload.city}")
 u=User(city=payload.city); db.add(u); await db.flush(); db.add(UserPreference(user_id=u.id)); await db.commit(); return {'id':u.id,'city':u.city}

@router.put('/{user_id}/city')
async def update_city(user_id:UUID,payload:CityUpdate,db:AsyncSession=Depends(get_db)):
 if not is_supported_city(payload.city): raise HTTPException(400,f"Unsupported city: {payload.city}")
 u=await db.get(User,user_id)
 if not u: raise HTTPException(404,'User not found')
 u.city=payload.city
 await db.commit()
 return {'ok':True,'city':u.city}

@router.put('/{user_id}/preferences')
async def preferences(user_id:UUID,payload:Prefs,db:AsyncSession=Depends(get_db)):
 u=await db.get(User,user_id)
 if not u: raise HTTPException(404,'User not found')
 pref=await db.get(UserPreference,user_id) or UserPreference(user_id=user_id)
 if payload.budget_max is None and payload.budget:
  if payload.budget.isdigit(): payload.budget_max=int(payload.budget)
  elif payload.budget == 'free': payload.budget_max=0
 if payload.budget_max is None and payload.budget_text:
  payload.budget_max=_parse_budget_text(payload.budget_text)
 if payload.duration_min is None and payload.duration:
  duration_ranges={'short':(0,120),'medium':(0,240),'long':(0,1440)}
  if payload.duration in duration_ranges: payload.duration_min,payload.duration_max=duration_ranges[payload.duration]
 if payload.duration_min is None and payload.duration_text:
  payload.duration_min,payload.duration_max=_parse_duration_text(payload.duration_text)
 when_label=_answer_label(payload.when,payload.when_text,WHEN_LABELS) or payload.preferred_period
 company_label=_answer_label(payload.company_size or payload.company,payload.company_text,COMPANY_LABELS)
 vibe_label=_answer_label(payload.vibe,payload.vibe_text,VIBE_LABELS)
 duration_label=_answer_label(payload.duration,payload.duration_text,DURATION_LABELS)
 budget_label=(
  'только бесплатные события' if payload.budget_max == 0 else
  f'до {payload.budget_max} рублей' if payload.budget_max is not None else
  (payload.budget_text.strip() if payload.budget_text and payload.budget_text.strip() else None)
 )
 profile='; '.join(filter(None,[
  f"Интересы: {', '.join(payload.categories+payload.genres)}" if payload.categories or payload.genres else None,
  f'Когда: {when_label}' if when_label else None,
  f'Компания: {company_label}' if company_label else None,
  f'Настроение: {vibe_label}' if vibe_label else None,
  f'Длительность: {duration_label}' if duration_label else None,
  f'Бюджет: {budget_label}' if budget_label else None,
 ]))
 # Keep the legacy ``company`` field populated for older rankers while the
 # questionnaire stores its normalized value in ``company_size``.  The
 # onboarding client intentionally sends the newer field, so falling back
 # here avoids silently dropping this preference for compatibility paths.
 pref.categories=payload.categories; pref.genres=payload.genres; pref.budget_max=payload.budget_max; pref.preferred_period=payload.preferred_period; pref.company=payload.company or payload.company_size; pref.novelty_preference=payload.novelty_preference; pref.profile_text=profile
 pref.when=payload.when; pref.when_text=payload.when_text; pref.company_size=payload.company_size; pref.company_text=payload.company_text; pref.vibe=payload.vibe; pref.vibe_text=payload.vibe_text; pref.duration_min=payload.duration_min; pref.duration_max=payload.duration_max; pref.duration_text=payload.duration_text; pref.budget_text=payload.budget_text; pref.questionnaire_version=payload.questionnaire_version
 embedding_ready=False
 if profile:
  try:
   pref.profile_embedding=await asyncio.to_thread(get_text_encoder().encode_query,profile)
   embedding_ready=True
  except Exception:
   # Preserve questionnaire data even if the model is temporarily unavailable.
   # Recommendation endpoint will return profile_embedding_unavailable instead of
   # inventing a personalized result from generic signals.
   pref.profile_embedding=None
 db.add(pref); await db.commit(); return {'ok':True,'profile_text':profile,'embedding_ready':embedding_ready}

@router.post('/{user_id}/interactions')
async def interaction(user_id:UUID,payload:Action,db:AsyncSession=Depends(get_db)):
 if payload.action not in {'view','like','dislike','save','share'}: raise HTTPException(400,'Unknown action')
 if not await db.get(User,user_id): raise HTTPException(404,'User not found')
 if not await db.get(Event,payload.event_id): raise HTTPException(404,'Event not found')
 db.add(Interaction(user_id=user_id,event_id=payload.event_id,action=payload.action,feed_request_id=payload.run_id,position=payload.position,model_version=payload.algorithm_version or ('questionnaire_podium' if payload.surface else None)))
 if payload.action=='save':
  existing=await db.get(SavedEvent,{'user_id':user_id,'event_id':payload.event_id})
  if not existing: db.add(SavedEvent(user_id=user_id,event_id=payload.event_id))
 await db.commit(); return {'ok':True}
