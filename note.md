일단 정상 작동은 함

-------------------
# 해야할 일

- 제목이 마지막이면 편집 모드에 들어갔을 때 글자가 커짐
- 리사이징 구현
- 메모 여러개 사용 가능하게 해보기
- 이거 체크 박스 만들고 싶은데 만드는건 둘째치고 리드 온리라 인터렉트가 안되는거 같음 

정규식으로 마크다운 구현하는 코드

볼드체 스타일
<code type="python">
bold_format = QTextCharFormat() bold_format.setFontWeight(QFont.Bold) self.highlighting_rules.append((QRegularExpression("\\*\\*.*\\*\\*"), bold_format)) self.highlighting_rules.append((QRegularExpression("__.*__"), bold_format))
<code/>


[ ]ddddd
[X]ddddd