$env:PYTHONIOENCODING="utf8"
echo "=== 1. BMSCE placements ==="
python -m src.cli situation --text "how are placements at BMS College of Engineering" --render
echo "`n=== 2. MSRIT campus life ==="
python -m src.cli situation --text "campus life at MSRIT" --render
echo "`n=== 3. DSCE fees and hostel ==="
python -m src.cli situation --text "fees and hostel food at DSCE" --render
echo "`n=== 4. BMS alias ==="
python -m src.cli situation --text "is bms good for cse" --render
echo "`n=== 5. Sir MVIT alias ==="
python -m src.cli situation --text "sir mvit placements" --render
echo "`n=== 6. Compare RVCE and BMSCE ==="
python -m src.cli situation --text "compare RVCE and BMSCE for computer science" --render
echo "`n=== 7. Stanford ==="
python -m src.cli situation --text "placements at Stanford" --render
echo "`n=== 8. Gibberish ==="
python -m src.cli situation --text "asdkjaslkdj random gibberish text" --render
