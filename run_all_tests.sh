#!/bin/bash
# Run all LegacyHelper tests and verifications

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║        LegacyHelper - Complete Test Suite                 ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check if venv is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Virtual environment not activated"
    echo "Run: source .venv/bin/activate"
    exit 1
fi

echo "1️⃣  Running unit tests..."
python -m pytest test/ -v --tb=short
echo ""

echo "2️⃣  Testing TUI initialization..."
python test_tui.py
echo ""

echo "3️⃣  Testing async conversation handling..."
python test_conversation.py
echo ""

echo "4️⃣  Testing command parser demo..."
python demo_parser.py | head -50
echo "   (showing first 50 lines, see full output by running: python demo_parser.py)"
echo ""

echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    ✅ ALL TESTS PASSED                     ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Ready to run the TUI! Set your API key and run:"
echo "  export GEMINI_API_KEY='your-key-here'"
echo "  python main.py"
echo ""
