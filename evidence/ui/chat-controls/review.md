# Composer permissions and speed controls

The supplied phone reference guided a shield on the left and a speedometer beside the microphone. Desktop controls retain text labels; phone controls retain accessible names, 44px targets and labeled menus. The speed menu saves Auto or a manual model and reasoning effort per chat. The header reflects the saved choice. Auto selects both for every ask; manual choices retain native acknowledgement and exact input, and skip Jev.

New chats snapshot the last successfully selected permissions; existing chats retain their choices. Permission preference and chat state save atomically. Creation sends the snapshot in native thread/start and saves it after success.

Backend tests verify manual sends, Auto restoration, thread isolation, invalid choices, native acknowledgement rejection and new-chat inheritance. Native offline checks exercise real manual settings and inspect effective permission policies on newly created chats for all presets. Frontend checks exercise matching acknowledgements without automatic retries. Targeted Firefox checks use the production bundle and synthetic data; screenshots and checks.json record desktop/narrow-phone operation.

## Gaps

No paid routing/inference or real automatic-review decision was exercised. Model/effort starts at Auto on new chats; only permission choices inherit. The unrelated broad browser typing fixture issue remains recorded in specs/verification.md.
