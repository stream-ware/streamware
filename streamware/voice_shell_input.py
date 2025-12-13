"""
Voice Shell Input Processing

Input processing mixin for the voice shell server.
Extracted from voice_shell_server.py for modularity.
"""

from .voice_shell_events import EventType, Event


class VoiceInputProcessorMixin:
    """Mixin class providing process_input method for VoiceShellServer."""
    
    async def process_input(self, text: str):
        """Process user input through LLM shell."""
        if not text.strip():
            return
        
        lower = text.lower().strip()
        
        # Multi-language cancel keywords - can cancel at ANY stage
        cancel_words = (
            # English
            "cancel", "stop", "nevermind", "never mind", "abort", "quit", "reset",
            # Polish
            "anuluj", "przerwij", "stop", "koniec", "zrezygnuj", "cofnij",
            # German
            "abbrechen", "stopp", "beenden", "zurück",
            # Spanish
            "cancelar", "parar", "detener",
            # French
            "annuler", "arrêter", "arreter",
        )
        
        # Multi-language confirmation keywords
        confirm_words = (
            # English
            "yes", "yeah", "okay", "ok", "execute", "do it", "run", "confirm", "sure",
            # Polish
            "tak", "dobrze", "wykonaj", "potwierdź", "potwierdzam", "zgoda",
            # German
            "ja", "jawohl", "ausführen", "bestätigen",
            # Spanish
            "sí", "si", "vale", "ejecutar",
            # French
            "oui", "d'accord", "exécuter",
        )
        
        # Multi-language rejection keywords
        reject_words = (
            # English
            "no", "nope", "don't", "dont",
            # Polish
            "nie", "niedobrze",
            # German
            "nein",
            # Spanish/French
            "non",
        )
        
        # Check for cancel at ANY stage - this takes priority
        if any(w == lower or lower.startswith(w + " ") for w in cancel_words):
            # Clear all pending states
            had_pending = self.pending_command or self.pending_options or self.pending_input_type
            self.pending_command = None
            self.pending_options = None
            self.pending_input_type = None
            self.pending_command_template = None
            self.spelling_buffer = ""
            
            if had_pending:
                await self.speak(self.t.conv("goal_cancelled"))
            else:
                await self.speak(self.t.conv("how_can_help"))
            return
        
        # Handle yes/no for pending command confirmation
        if self.pending_command and lower in confirm_words:
            await self.execute_command(self.pending_command)
            self.pending_command = None
            return
        
        if self.pending_command and lower in reject_words:
            self.pending_command = None
            await self.speak(self.t.conv("goal_cancelled"))
            return
        
        # Handle option selection (1, 2, 3, one, two, three) - multi-language
        if self.pending_options:
            option_map = {
                # English
                "one": "1", "1": "1", "first": "1",
                "two": "2", "2": "2", "second": "2", 
                "three": "3", "3": "3", "third": "3",
                "four": "4", "4": "4", "fourth": "4",
                # Polish
                "jeden": "1", "pierwsza": "1", "pierwszą": "1", "pierwszy": "1",
                "dwa": "2", "druga": "2", "drugą": "2", "drugi": "2",
                "trzy": "3", "trzecia": "3", "trzecią": "3", "trzeci": "3",
                "cztery": "4", "czwarta": "4", "czwartą": "4", "czwarty": "4",
                # German
                "eins": "1", "erste": "1", "ersten": "1",
                "zwei": "2", "zweite": "2", "zweiten": "2",
                "drei": "3", "dritte": "3", "dritten": "3",
                "vier": "4", "vierte": "4", "vierten": "4",
            }
            choice = option_map.get(lower, lower)
            
            matched = False
            for key, desc, cmd in self.pending_options:
                if choice == key:
                    matched = True
                    self.pending_options = None
                    if cmd == "need_email":
                        # Use live narrator with track mode for better person detection
                        # Email is passed via SQ_NOTIFY_EMAIL env variable
                        self.pending_command_template = f"SQ_NOTIFY_EMAIL={{email}} sq live narrator --mode track --focus person --duration 60 --skip-checks --adaptive"
                        
                        # Check if email is already saved
                        saved_email = self.shell.context.get("email")
                        if saved_email:
                            # Offer to use saved email
                            self.pending_input_type = "use_saved_email"
                            await self.broadcast(Event(
                                type=EventType.TTS_SPEAK,
                                data={"text": f"I have your email saved as {saved_email}. Say 'yes' to use it, or 'new' to enter a different email."}
                            ))
                        else:
                            self.pending_input_type = "email"
                            await self.broadcast(Event(
                                type=EventType.TTS_SPEAK,
                                data={"text": "Please say your email address. You can spell it letter by letter."}
                            ))
                        return
                    elif cmd == "functions":
                        await self.broadcast(Event(
                            type=EventType.TTS_SPEAK,
                            data={"text": self.shell._list_functions()}
                        ))
                        return
                    else:
                        # Store selected command for confirmation
                        result = ShellResult(understood=True, shell_command=cmd, explanation=desc)
                        self.pending_command = result
                        
                        await self.broadcast(Event(
                            type=EventType.COMMAND_PARSED,
                            data={
                                "input": text,
                                "understood": True,
                                "explanation": desc,
                                "command": cmd,
                            }
                        ))
                        await self.broadcast(Event(
                            type=EventType.TTS_SPEAK,
                            data={"text": f"{desc}. Say yes to confirm."}
                        ))
                        return
            
            if not matched:
                # Check if this looks like a new command (not a number/option)
                # If so, clear pending options and process as new command
                all_option_words = set(option_map.keys())
                if choice not in all_option_words:
                    # User said something else - treat as new command
                    self.pending_options = None
                    # Fall through to process as new command (don't return)
                else:
                    # Invalid option number - repeat options (with cancel hint)
                    options_text = self.t.conv("say_cancel_anytime") + " "
                    for key, desc, _ in self.pending_options:
                        options_text += f"{key}: {desc}. "
                    await self.broadcast(Event(
                        type=EventType.TTS_SPEAK,
                        data={"text": options_text}
                    ))
                    return
        
        # Handle saved email confirmation
        if self.pending_input_type == "use_saved_email":
            saved_email = self.shell.context.get("email")
            
            # User wants to use saved email - execute immediately
            if lower in confirm_words:
                cmd = self.pending_command_template.replace("{email}", saved_email)
                result = ShellResult(understood=True, shell_command=cmd, explanation=f"Detect and email {saved_email}")
                self.pending_input_type = None
                self.pending_command_template = None
                
                await self.broadcast(Event(
                    type=EventType.CONTEXT_UPDATED,
                    data=self.shell.context
                ))
                
                await self.speak(self.t.conv("using_email", email=saved_email))
                
                # Execute command directly without requiring second confirmation
                await self.execute_command(result)
                return
            
            # User wants new email (multi-language)
            new_email_words = (
                "new", "different", "change", "other",  # English
                "nowy", "inny", "zmień", "zmien", "inna",  # Polish
                "neu", "andere", "ändern", "andern",  # German
            )
            if lower in reject_words or any(w in lower for w in new_email_words):
                self.pending_input_type = "email"
                await self.speak(self.t.conv("enter_new_email"))
                return
            
            # Check if user said something that looks like a new command
            # If it's not a simple yes/no/new, treat as new command
            if len(lower.split()) > 2 or any(cmd_word in lower for cmd_word in ("track", "śledź", "opisz", "describe", "read", "czytaj", "która", "godzina")):
                self.pending_input_type = None
                self.pending_command_template = None
                # Fall through to process as new command
            else:
                # Repeat question
                await self.speak(self.t.conv("say_yes_or_new", email=saved_email))
                return
        
        # Handle email input (spelling mode)
        if self.pending_input_type == "email":
            # Multi-language done/confirm words
            done_words = (
                "done", "confirm", "finished", "complete",  # English
                "gotowe", "koniec", "potwierdź", "zakończ",  # Polish
                "fertig", "bestätigen", "abgeschlossen",  # German
            )
            
            # Multi-language clear/reset words
            clear_words = (
                "clear", "reset", "start over", "again",  # English
                "wyczyść", "od nowa", "jeszcze raz", "reset",  # Polish
                "löschen", "neu", "nochmal",  # German
            )
            
            # Multi-language delete/backspace words
            delete_words = (
                "delete", "backspace", "remove", "undo",  # English
                "usuń", "cofnij", "skasuj",  # Polish
                "löschen", "entfernen", "zurück",  # German
            )
            
            # Check for done/confirm - execute immediately
            if any(w in lower for w in done_words):
                if self.spelling_buffer:
                    email = self.spelling_buffer.replace(" ", "").lower()
                    cmd = self.pending_command_template.replace("{email}", email)
                    result = ShellResult(understood=True, shell_command=cmd, explanation=f"Detect and email {email}")
                    self.pending_input_type = None
                    self.pending_command_template = None
                    self.spelling_buffer = ""
                    
                    # Save email to shell context and database
                    self.shell.context["email"] = email
                    self.db.set_config("email", email)
                    
                    # Broadcast context update to UI
                    await self.broadcast(Event(
                        type=EventType.CONTEXT_UPDATED,
                        data=self.shell.context
                    ))
                    
                    await self.speak(self.t.conv("email_set", email=email))
                    
                    # Execute command directly
                    await self.execute_command(result)
                    return
            
            # Check for corrections
            if any(w in lower for w in clear_words):
                self.spelling_buffer = ""
                await self.speak(self.t.conv("enter_new_email"))
                return
            
            # Check for delete/backspace
            if any(w in lower for w in delete_words):
                if self.spelling_buffer:
                    self.spelling_buffer = self.spelling_buffer[:-1]
                # Use simple response (no translation needed for buffer state)
                await self.broadcast(Event(
                    type=EventType.TTS_SPEAK,
                    data={"text": f"Current: {self.spelling_buffer or 'empty'}"}
                ))
                return
            
            # Check if user said something that looks like a new command
            command_keywords = (
                "track", "detect", "describe", "read", "watch", "stop", "help", "hello",  # English
                "śledź", "wykryj", "opisz", "czytaj", "która", "godzina", "cześć", "pomoc",  # Polish
                "verfolgen", "erkennen", "beschreiben", "lesen", "hallo", "hilfe",  # German
            )
            if any(cmd_word in lower for cmd_word in command_keywords):
                # User wants to do something else - clear email input and process as command
                self.pending_input_type = None
                self.pending_command_template = None
                self.spelling_buffer = ""
                # Fall through to process as new command
            else:
                # Handle @ and . symbols (multi-language)
                clean_text = text.lower()
                # English
                clean_text = clean_text.replace(" at ", "@").replace(" dot ", ".").replace("at sign", "@")
                # Polish
                clean_text = clean_text.replace("małpa", "@").replace("kropka", ".").replace(" małpa ", "@").replace(" kropka ", ".")
                # German
                clean_text = clean_text.replace("klammeraffe", "@").replace("punkt", ".").replace(" at ", "@")
                
                # If looks like full email, just use it
                if "@" in clean_text and "." in clean_text:
                    self.spelling_buffer = clean_text.replace(" ", "")
                    await self.broadcast(Event(
                        type=EventType.TTS_SPEAK,
                        data={"text": f"{self.spelling_buffer}. {self.t.conv('say_yes_confirm')}"}
                    ))
                    return
                
                # Add to buffer
                self.spelling_buffer += clean_text.replace(" ", "")
                await self.broadcast(Event(
                    type=EventType.TTS_SPEAK,
                    data={"text": f"{self.spelling_buffer}. {self.t.conv('say_cancel_anytime')}"}
                ))
                return
        
        # Parse with LLM shell
        result = self.shell.parse(text)
        
        # Handle special commands first (no broadcast needed)
        if result.function_name in ("help", "list", "history", "context", "set_url", "set_email"):
            await self.broadcast(Event(
                type=EventType.TTS_SPEAK,
                data={"text": result.explanation}
            ))
            return
        
        if result.function_name == "stop":
            await self.stop_process()
            return
        
        # Handle clarification with options (single broadcast with options)
        if result.function_name == "clarify" and result.options:
            self.pending_options = result.options
            options_text = result.explanation + " "
            for key, desc, _ in result.options:
                options_text += f"{key}: {desc}. "
            
            # Log options to session and database
            session = self.get_current_session()
            if session:
                question_line = f"❓ {result.explanation}"
                session.output.append(question_line)
                self.db.log_output(session.id, question_line, "system")
                for key, desc, _ in result.options:
                    opt_line = f"   {key}. {desc}"
                    session.output.append(opt_line)
                    self.db.log_output(session.id, opt_line, "system")
            
            await self.broadcast(Event(
                type=EventType.COMMAND_PARSED,
                data={
                    "input": text,
                    "understood": True,
                    "explanation": result.explanation,
                    "options": [(k, d) for k, d, _ in result.options],
                }
            ))
            await self.broadcast(Event(
                type=EventType.TTS_SPEAK,
                data={"text": options_text}
            ))
            return
        
        # Broadcast parsed result for other commands
        await self.broadcast(Event(
            type=EventType.COMMAND_PARSED,
            data={
                "input": text,
                "understood": result.understood,
                "explanation": result.explanation,
                "command": result.shell_command,
                "function": result.function_name,
            }
        ))
        
        # Handle need_input for email, etc.
        if result.function_name == "need_input":
            self.pending_input_type = result.input_type
            self.pending_command_template = result.pending_command
            
            await self.broadcast(Event(
                type=EventType.TTS_SPEAK,
                data={"text": result.explanation}
            ))
            return
        
        if not result.understood:
            await self.speak(self.t.conv("not_understood", text=text))
            return
        
        # Store pending command
        if result.shell_command:
            self.pending_command = result
            
            # Auto-inject URL from context
            missing, cmd = self.shell._check_missing_params(result.shell_command)
            
            if missing:
                # Ask for missing params
                await self.broadcast(Event(
                    type=EventType.TTS_SPEAK,
                    data={"text": f"Missing {', '.join(missing)}. Please provide the value."}
                ))
            else:
                # Speak the explanation and wait for confirm
                await self.broadcast(Event(
                    type=EventType.TTS_SPEAK,
                    data={"text": f"{result.explanation}. Say 'yes' to execute or 'no' to cancel."}
                ))
    

    async def handle_message(self, websocket, message: str):
        """Handle incoming message from client."""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "text_input")
            content = data.get("content", "")
            
            # Session management commands
            if msg_type == "new_session":
                session = self.create_session(content or None)
                await self.broadcast(Event(
                    type=EventType.SESSION_CREATED,
                    data={"session": session.to_dict(), "sessions": self._get_sessions_list()}
                ))
                await self.speak(self.t.status("new_conversation"))
                return
            
            elif msg_type == "switch_session":
                session = self.switch_session(content)
                if session:
                    await self.broadcast(Event(
                        type=EventType.SESSION_SWITCHED,
                        data={
                            "session": session.to_dict(), 
                            "output": session.output[-100:],  # Last 100 lines
                            "sessions": self._get_sessions_list()
                        }
                    ))
                else:
                    # Session not found - send error
                    await self.broadcast(Event(
                        type=EventType.SESSION_OUTPUT,
                        data={"session_id": self.current_session_id, "line": f"⚠️ Session {content} not found. Available: {list(self.sessions.keys())}"}
                    ))
                return
            
            elif msg_type == "close_session":
                self.close_session(content)
                await self.broadcast(Event(
                    type=EventType.SESSION_CLOSED,
                    data={"session_id": content, "sessions": self._get_sessions_list()}
                ))
                return
            
            elif msg_type == "get_sessions":
                # Create first session if none exist
                if not self.sessions:
                    session = self.create_session()
                    await self.broadcast(Event(
                        type=EventType.SESSION_CREATED,
                        data={"session": session.to_dict(), "sessions": self._get_sessions_list()}
                    ))
                    await self.speak(self.t.status("new_conversation"))
                else:
                    # Send existing sessions with current session output
                    current_session = self.get_current_session()
                    await websocket.send(json.dumps({
                        "type": "sessions_list",
                        "data": {
                            "sessions": self._get_sessions_list(), 
                            "current": self.current_session_id,
                            "output": current_session.output[-100:] if current_session else []
                        }
                    }))
                return
            
            elif msg_type == "voice_input":
                # Voice input from browser STT
                # Store to session output for history AND database
                session = self.get_current_session()
                if session:
                    line = f"> {content}"
                    session.output.append(line)
                    self.db.log_output(session.id, line, "input")
                
                await self.broadcast(Event(
                    type=EventType.VOICE_INPUT,
                    data={"text": content, "source": "browser_stt"}
                ))
                await self.process_input(content)
                
            elif msg_type == "text_input":
                # Text input
                # Store to session output for history AND database
                session = self.get_current_session()
                if session:
                    line = f"> {content}"
                    session.output.append(line)
                    self.db.log_output(session.id, line, "input")
                
                await self.broadcast(Event(
                    type=EventType.TEXT_INPUT,
                    data={"text": content}
                ))
                await self.process_input(content)
                
            elif msg_type == "confirm":
                # Confirm pending command
                if self.pending_command:
                    await self.execute_command(self.pending_command)
                    self.pending_command = None
                    
            elif msg_type == "cancel":
                # Cancel pending command
                if self.pending_command:
                    await self.broadcast(Event(
                        type=EventType.COMMAND_CANCEL,
                        data={"command": self.pending_command.shell_command}
                    ))
                    self.pending_command = None
                    
            elif msg_type == "stop":
                # Stop current session's process
                await self.stop_current_session()
            
            elif msg_type == "stop_session":
                # Stop specific session's process by ID
                await self.stop_session_by_id(content)
            
            elif msg_type == "set_language":
                # Set conversation language (CQRS command - persists to SQLite)
                self.language = content
                self.shell.language = content
                self.shell.t.set_language(content)  # Update shell translator
                self.t.set_language(content)  # Update server translator
                self.db.set_config("language", content)
                
                # Record event (event sourcing)
                self.events.append(Event(
                    type=EventType.LANGUAGE_CHANGED,
                    data={"language": content}
                ))
                
                # Broadcast to all clients
                await self.broadcast(Event(
                    type=EventType.LANGUAGE_CHANGED,
                    data={"language": content}
                ))
                print(f"🌐 Language set to: {content}", flush=True)
            
            elif msg_type == "get_config":
                # CQRS query - return current config from SQLite
                await self._send_config(websocket)
            
            elif msg_type == "set_variable":
                # CQRS command - set variable in context and SQLite
                key = content.get("key")
                value = content.get("value")
                if key:
                    # Update shell context
                    self.shell.context[key] = value
                    # Persist to SQLite
                    self.db.set_config(key, value)
                    
                    # Record event (event sourcing)
                    self.events.append(Event(
                        type=EventType.VARIABLE_CHANGED,
                        data={"key": key, "value": value}
                    ))
                    
                    # Broadcast to all clients
                    await self.broadcast(Event(
                        type=EventType.VARIABLE_CHANGED,
                        data={"key": key, "value": value}
                    ))
                    print(f"📝 Variable set: {key}={value[:50] if value else '(empty)'}...", flush=True)
            
            elif msg_type == "remove_variable":
                # CQRS command - remove variable
                key = content.get("key")
                if key and key in self.shell.context:
                    del self.shell.context[key]
                    self.db.set_config(key, "")  # Clear in SQLite
                    
                    # Broadcast removal
                    await self.broadcast(Event(
                        type=EventType.VARIABLE_CHANGED,
                        data={"key": key, "value": None, "removed": True}
                    ))
                    print(f"🗑️ Variable removed: {key}", flush=True)
                
        except json.JSONDecodeError:
            # Plain text input
            await self.process_input(message)
    
