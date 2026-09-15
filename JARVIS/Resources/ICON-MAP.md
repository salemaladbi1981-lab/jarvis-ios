# JARVIS — Icon Map

## Style Lock
- Thin outline (stroke 1.5px)
- Geometric, rounded caps/joins
- Cyan/ice-blue active, dim gray-blue inactive
- Single coherent family (shared custom SVG), no emoji, no mixed packs
- Custom SVG where stock icon differs from reference

## Families → canonical implementation
| Family | icon_id | Source | Asset | Stroke | Size Token | Notes |
|---|---|---|---|---|---|---|
| Home | `nav.home` | custom-svg | jarvis_home_24 | icon.stroke.default | icon.md | house outline |
| Devices | `nav.devices` | custom-svg | jarvis_devices_24 | icon.stroke.default | icon.md | sunburst / 8-spoke |
| Car | `nav.car` | custom-svg | jarvis_car_24 | icon.stroke.default | icon.md | sedan side |
| Calendar | `nav.calendar` | custom-svg | jarvis_calendar_24 | icon.stroke.default | icon.md | grid + top ticks |
| Messages | `nav.messages` | custom-svg | jarvis_messages_24 | icon.stroke.default | icon.md | envelope / mail outline (per reference) |
| Files | `nav.files` | custom-svg | jarvis_files_24 | icon.stroke.default | icon.md | folder |
| Settings | `nav.settings` | custom-svg | jarvis_settings_24 | icon.stroke.default | icon.md | gear |
| Night Mode | `nav.night` | custom-svg | jarvis_night_24 | icon.stroke.default | icon.md | crescent |
| Logout | `nav.logout` | custom-svg | jarvis_logout_24 | icon.stroke.default | icon.md | arrow out |
| Light | `home.light` | custom-svg | jarvis_light_24 | icon.stroke.default | icon.md | bulb rays |
| AC / Snowflake | `home.ac` | custom-svg | jarvis_ac_24 | icon.stroke.default | icon.md | snowflake |
| Curtains | `home.curtains` | custom-svg | jarvis_curtains_24 | icon.stroke.default | icon.md | blinds |
| TV | `home.tv` | custom-svg | jarvis_tv_24 | icon.stroke.default | icon.md | rectangle + legs |
| Shield | `sec.shield` | custom-svg | jarvis_shield_24 | icon.stroke.default | icon.md | shield |
| Camera | `sec.camera` | custom-svg | jarvis_camera_24 | icon.stroke.default | icon.md | camera + lens |
| Door / Lock | `sec.lock` | custom-svg | jarvis_lock_24 | icon.stroke.default | icon.md | lock |
| LIVE indicator | `sec.live` | custom-svg | jarvis_live_24 | icon.stroke.default | icon.md | pulsing red dot |
| Music | `media.music` | custom-svg | jarvis_music_24 | icon.stroke.default | icon.md | note / disc |
| Previous | `media.prev` | custom-svg | jarvis_prev_24 | icon.stroke.default | icon.md | prev arrow |
| Play/Pause | `media.play` | custom-svg | jarvis_play_24 | icon.stroke.default | icon.md | play triangle |
| Next | `media.next` | custom-svg | jarvis_next_24 | icon.stroke.default | icon.md | next arrow |
| Search | `util.search` | custom-svg | jarvis_search_24 | icon.stroke.default | icon.md | magnifier |
| Bell | `util.bell` | custom-svg | jarvis_bell_24 | icon.stroke.default | icon.md | bell |
| Profile | `util.profile` | custom-svg | jarvis_profile_24 | icon.stroke.default | icon.md | person circle |
| Tasks | `data.tasks` | custom-svg | jarvis_tasks_24 | icon.stroke.default | icon.md | checklist (checkbox rows) |
| Checkbox | `data.checkbox` | custom-svg | jarvis_checkbox_24 | icon.stroke.default | icon.md | check square |
| Calendar markers | `data.calmark` | custom-svg | jarvis_calmark_24 | icon.stroke.default | icon.md | colored timeline dots |
| Weather | `data.weather` | custom-svg | jarvis_weather_24 | icon.stroke.default | icon.md | sun + rays |
| Microphone | `util.mic` | custom-svg | jarvis_mic_24 | icon.stroke.default | icon.md | mic |
| Send | `util.send` | custom-svg | jarvis_send_24 | icon.stroke.default | icon.md | paper plane |
| More | `util.more` | custom-svg | jarvis_more_24 | icon.stroke.default | icon.md | 3 dots |

## Agent Icons → canonical IDs
| Agent | icon_id | Source | Asset | Symbol |
|---|---|---|---|---|
| المنسق | `agent.core.coordinator` | custom-svg | agent_core_coordinator_24 | orbit |
| المراقب | `agent.core.watcher` | custom-svg | agent_core_watcher_24 | eye |
| المنتج | `agent.core.producer` | custom-svg | agent_core_producer_24 | film |
| الصفقات | `agent.core.dealmaker` | custom-svg | agent_core_dealmaker_24 | briefcase |
| الحارس | `agent.core.guardian` | custom-svg | agent_core_guardian_24 | shield |
| الكاتب | `agent.core.writer` | custom-svg | agent_core_writer_24 | pen |
| المراجع | `agent.core.reviewer` | custom-svg | agent_core_reviewer_24 | check |
| البيت | `agent.core.home` | custom-svg | agent_core_home_24 | home |
| البناء | `agent.system.builder` | custom-svg | agent_system_builder_24 | hammer |
| المدرب | `agent.system.coach` | custom-svg | agent_system_coach_24 | target |
| الربع | `agent.system.circle` | custom-svg | agent_system_circle_24 | users |
| الخادم | `agent.system.server` | custom-svg | agent_system_server_24 | server |
| معمار | `agent.system.architect` | custom-svg | agent_system_architect_24 | blueprint |
| مدير العميل | `agent.content.account` | custom-svg | agent_content_account_24 | folder |
| المدير الإبداعي | `agent.content.creative` | custom-svg | agent_content_creative_24 | bulb |
| المخرج | `agent.content.director` | custom-svg | agent_content_director_24 | clapper |
| كاتب السيناريو | `agent.content.scriptwriter` | custom-svg | agent_content_scriptwriter_24 | script |
| مهندس البرومبت | `agent.content.prompteng` | custom-svg | agent_content_prompteng_24 | terminal |
| مصمم الحركة | `agent.content.motion` | custom-svg | agent_content_motion_24 | waveform |
| مراقب الجودة | `agent.content.qc` | custom-svg | agent_content_qc_24 | check-circle |
| مراجع التسويق | `agent.content.mkt` | custom-svg | agent_content_mkt_24 | megaphone |

## Orbit node policy
- Agent orbit nodes are **label-only** when an icon is not visually required at 8/5-node density.
- Active node uses `glow.agent_active`; inactive uses `glow.agent_inactive` (see DESIGN-TOKENS.json).
