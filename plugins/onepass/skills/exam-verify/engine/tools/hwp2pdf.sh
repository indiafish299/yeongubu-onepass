#!/bin/zsh
# 한컴오피스 한글 Viewer(맥)로 .hwp/.hwpx 를 PDF 로 저장한다. 조판은 한컴 엔진 그대로.
# 쓰는 법: hwp2pdf.sh --allow-front <입력.hwp> <출력.pdf>
# 뷰어는 뒤에 있으면 인쇄 메뉴·버튼·단축키가 모두 꺼진다(11/22 확인). 그래서 10~15초 동안 뷰어 창이 앞으로 나온다.
# 선생님이 맥을 쓰는 중에는 돌리지 않는다. --allow-front 는 선생님이 「지금 돌려도 된다」고 한 뒤에만 붙인다.
# 키 입력을 보내지 않는다(사용자가 다른 창에 글을 쓰는 중이어도 끼어들지 않게 버튼만 직접 누른다).
set -e
[ "$1" = "--allow-front" ] || { echo "거부: 뷰어 창이 앞으로 나온다. 선생님 허락 뒤 --allow-front 를 붙여 돌린다"; exit 2; }
shift
IN="$1"; OUT="$2"
[ -f "$IN" ] || { echo "입력 없음: $IN"; exit 2; }
[ -e "$OUT" ] && { echo "출력이 이미 있음(덮어쓰지 않음): $OUT"; exit 2; }
TMP="ev_hwp2pdf_$$_$RANDOM"
DOC="$HOME/Documents/$TMP.pdf"
open -g -a "Hancom Office HWP Viewer" "$IN"
osascript - "$TMP" <<'OSA'
on run argv
  set tmpName to item 1 of argv
  tell application "System Events"
    set p to (first process whose bundle identifier is "com.haansoft.HancomOfficeViewer.Mac")
    repeat 40 times
      if (count of windows of p) > 0 then exit repeat
      delay 0.5
    end repeat
    delay 3
    -- 메뉴는 앱이 앞에 있어야 눌린다. 앞으로 가져오되 키 입력은 보내지 않는다.
    tell application "Hancom Office HWP Viewer" to activate
    delay 1.5
    tell p
      -- 방금 연 문서가 맨 앞 창(window 1)이다
      click menu item "인쇄..." of menu 1 of menu bar item "파일" of menu bar 1
      repeat 40 times
        if (count of sheets of window 1) > 0 then exit repeat
        delay 0.5
      end repeat
      delay 2
      click button 1 of group 2 of splitter group 1 of sheet 1 of window 1
      repeat 40 times
        try
          if (count of sheets of sheet 1 of window 1) > 0 then exit repeat
        end try
        delay 0.5
      end repeat
      delay 1
      set sv to splitter group 1 of sheet 1 of sheet 1 of window 1
      set loc to value of (first pop up button of sv whose name is "위치:")
      if loc is not "문서" then error "저장 위치가 문서 폴더가 아님: " & loc
      set value of (first text field of sv whose name is "별도 저장:") to tmpName
      delay 0.5
      click button "저장" of sv
      repeat 60 times
        if (count of sheets of window 1) = 0 then exit repeat
        delay 0.5
      end repeat
      delay 1
      tell application "Hancom Office HWP Viewer" to activate
      delay 1
      click menu item "문서 닫기" of menu 1 of menu bar item "파일" of menu bar 1
    end tell
  end tell
end run
OSA
for i in $(seq 1 20); do [ -s "$DOC" ] && break; sleep 0.5; done
[ -s "$DOC" ] || { echo "PDF가 만들어지지 않음"; exit 3; }
mv "$DOC" "$OUT"
echo "$OUT"
