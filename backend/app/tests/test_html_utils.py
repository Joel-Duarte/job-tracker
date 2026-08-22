from app.core.html_utils import clean_html_text


def test_clean_html_text_plain_text():
    raw = "Hello, this is already plain text.\nBest regards,\nRecruiter"
    assert clean_html_text(raw) == raw


def test_clean_html_text_none_and_empty():
    assert clean_html_text(None) == ""
    assert clean_html_text("") == ""
    assert clean_html_text("   \n\t  ") == ""


def test_clean_html_text_strips_scripts_and_styles():
    raw = """
    <html>
        <head>
            <style>body { color: red; font-size: 14px; }</style>
            <script>console.log("tracking pixel");</script>
        </head>
        <body>
            <p>Thank you for applying to <strong>Stripe</strong>!</p>
            <script type="text/javascript">var x = 10;</script>
        </body>
    </html>
    """
    result = clean_html_text(raw)
    assert "Thank you for applying to Stripe!" in result
    assert "color: red" not in result
    assert "console.log" not in result
    assert "var x = 10" not in result


def test_clean_html_text_decodes_entities_and_formats_breaks():
    raw = """
    <div>Dear Candidate,&nbsp;&amp;&nbsp;Future Colleague,</div>
    <div>We&#39;d like to invite you for an &quot;Initial Screen&quot;.</div>
    <br/>
    <p>Please review our open roles:</p>
    <ul>
        <li>Staff Engineer</li>
        <li>Principal Architect</li>
    </ul>
    """
    result = clean_html_text(raw)
    assert "Dear Candidate, & Future Colleague," in result
    assert 'We\'d like to invite you for an "Initial Screen".' in result
    assert "Please review our open roles:" in result
    assert "Staff Engineer" in result
    assert "Principal Architect" in result
    assert "<div" not in result
    assert "<li" not in result
    assert "&nbsp;" not in result
