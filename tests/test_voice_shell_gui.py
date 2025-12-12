"""
Tests for Voice Shell GUI functionality.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_session_creation():
    """Test that sessions are created with correct IDs."""
    from streamware.voice_shell_server import VoiceShellServer
    
    server = VoiceShellServer(port=9999)
    
    # Clear restored sessions for fresh test
    server.sessions.clear()
    server._session_counter = 0
    server.current_session_id = None
    
    session1 = server.create_session("Test Session 1")
    assert session1.id == "s1", f"Expected s1, got {session1.id}"
    assert session1.name == "Test Session 1"
    assert session1.status == "idle"
    
    session2 = server.create_session("Test Session 2")
    assert session2.id == "s2", f"Expected s2, got {session2.id}"
    assert server.current_session_id == "s2"


def test_session_switching():
    """Test switching between sessions."""
    from streamware.voice_shell_server import VoiceShellServer
    
    server = VoiceShellServer(port=9998)
    
    # Clear restored sessions for fresh test
    server.sessions.clear()
    server._session_counter = 0
    server.current_session_id = None
    
    session1 = server.create_session("Session 1")
    session2 = server.create_session("Session 2")
    
    session1.output.append("Line 1 in session 1")
    session1.output.append("Line 2 in session 1")
    session2.output.append("Line 1 in session 2")
    
    switched = server.switch_session("s1")
    assert switched is not None
    assert switched.id == "s1"
    assert server.current_session_id == "s1"
    assert len(switched.output) == 2


def test_session_not_found():
    """Test switching to non-existent session."""
    from streamware.voice_shell_server import VoiceShellServer
    
    server = VoiceShellServer(port=9997)
    
    # Clear restored sessions for fresh test
    server.sessions.clear()
    server._session_counter = 0
    server.current_session_id = None
    
    server.create_session("Session 1")
    
    switched = server.switch_session("invalid_id")
    assert switched is None
    assert server.current_session_id == "s1"


def test_person_detected_sends_notification():
    """Test that person detection triggers notification."""
    from streamware.notification_filter import should_notify
    
    assert should_notify("Person entering from left", focus="person") == True
    assert should_notify("Person on left detected", focus="person") == True
    assert should_notify("A person is visible in the frame", focus="person") == True


def test_static_scene_no_notification():
    """Test that static scenes don't trigger notification."""
    from streamware.notification_filter import should_notify
    
    assert should_notify("Scene is still", focus="person") == False
    assert should_notify("No person visible", focus="person") == False


def test_focus_target_matching():
    """Test that focus target is correctly matched."""
    from streamware.notification_filter import should_notify
    
    assert should_notify("Car entering driveway", focus="car") == True
    assert should_notify("No car visible", focus="car") == False


def test_command_format():
    """Test that commands are formatted correctly."""
    from streamware.llm_shell import LLMShell
    
    shell = LLMShell()
    
    result = shell.parse("detect person")
    assert result.understood == True
    assert "sq live narrator" in result.shell_command
    assert "--focus person" in result.shell_command


def test_email_command_format():
    """Test email command uses env variable."""
    from streamware.llm_shell import LLMShell
    
    shell = LLMShell()
    
    result = shell.parse("email tom@example.com when person detected")
    assert result.understood == True
    assert "SQ_NOTIFY_EMAIL=tom@example.com" in result.shell_command


def test_output_preserved_on_switch():
    """Test that output is preserved when switching sessions."""
    from streamware.voice_shell_server import VoiceShellServer
    
    server = VoiceShellServer(port=9996)
    
    # Clear restored sessions for fresh test
    server.sessions.clear()
    server._session_counter = 0
    server.current_session_id = None
    
    session1 = server.create_session("Session 1")
    session2 = server.create_session("Session 2")
    
    test_lines = ["Line 1", "Line 2", "Line 3"]
    for line in test_lines:
        session1.output.append(line)
        
    server.switch_session("s2")
    server.switch_session("s1")
    
    current = server.get_current_session()
    assert current.id == "s1"
    assert len(current.output) == 3


def test_sessions_list():
    """Test that sessions list returns correct data."""
    from streamware.voice_shell_server import VoiceShellServer
    
    server = VoiceShellServer(port=9995)
    
    # Clear restored sessions for fresh test
    server.sessions.clear()
    server._session_counter = 0
    server.current_session_id = None
    
    s1 = server.create_session("Session A")
    s1.output.extend(["line1", "line2", "line3"])
    s1.status = "completed"
    
    s2 = server.create_session("Session B")
    s2.status = "running"
    
    sessions_list = server._get_sessions_list()
    
    assert len(sessions_list) == 2
    
    sa = next(s for s in sessions_list if s['name'] == 'Session A')
    assert sa['status'] == 'completed'
    assert sa['output_lines'] == 3


def test_language_translations():
    """Test that language translations are loaded correctly."""
    from streamware.i18n.translations import get_language, LANGUAGES, get_conversation_message
    
    # Check supported languages
    assert 'en' in LANGUAGES
    assert 'pl' in LANGUAGES
    assert 'de' in LANGUAGES
    
    # Check English
    en = get_language('en')
    assert en.voice_code == 'en-US'
    assert en.ui.yes == 'Yes'
    
    # Check Polish
    pl = get_language('pl')
    assert pl.voice_code == 'pl-PL'
    assert pl.ui.yes == 'Tak'
    
    # Check German
    de = get_language('de')
    assert de.voice_code == 'de-DE'
    assert de.ui.yes == 'Ja'
    
    # Check message formatting
    msg = get_conversation_message('pl', 'email_saved', email='test@example.com')
    assert 'test@example.com' in msg


def test_server_language_init():
    """Test that server initializes with language support."""
    from streamware.voice_shell_server import VoiceShellServer
    
    server = VoiceShellServer(port=9994)
    
    # Server should have language attribute
    assert hasattr(server, 'language')
    assert server.language in ['en', 'pl', 'de']


def run_tests():
    """Run all tests and report results."""
    passed = 0
    failed = 0
    
    tests = [
        test_session_creation,
        test_session_switching,
        test_session_not_found,
        test_person_detected_sends_notification,
        test_static_scene_no_notification,
        test_focus_target_matching,
        test_command_format,
        test_email_command_format,
        test_output_preserved_on_switch,
        test_sessions_list,
        test_language_translations,
        test_server_language_init,
    ]
    
    print("🧪 Running Voice Shell GUI Tests\n")
    
    for test in tests:
        try:
            test()
            print(f"✅ {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"💥 {test.__name__}: {type(e).__name__}: {e}")
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
