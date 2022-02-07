from io import TextIOWrapper

import cssutils
from cssutils.css.cssstyledeclaration import CSSStyleDeclaration

css_ = u'''

body, html { color: blue ;  border: 1px;
}
h1, h2 { font-size: 1.5em; color: red}
h3, h4, h5 { font-size: small; }
'''
css = u'''

body, html { color: blue }
h1, h2 { font-size: 1.5em; color: red}
h3, h4, h5 { font-size: small; }
h1 {
  font-size: 60px;
  text-align: center;
}

p, li {
  font-size: 16px;
  line-height: 2;
  letter-spacing: 1px;
}
body {
  width: 600px;
  margin: 0 auto;
  background-color: #FF9500;
  padding: 0 20px 20px 20px;
  border: 5px solid black;
  background-image: url(bg-graphic.png);
}
.outer {
  border: 5px solid black;
}

.box {
  padding: 10px;
  width: calc(90% - 30px);
  background-color: rebeccapurple;
  color: white;
}
'''
class SheetCSS:
    standart_css = css_
    def __init__(self, document, parent_doc=None) -> None:
        self.cssText = ""
        self.dctSheet = {}
        self.dctClasses = {}       
        self.cssSheet = None       
        if document:
            self.parseDocument(document, parent_doc)
    
    def __getText(self, document):
        if type(document) is TextIOWrapper:
            return document.read()
        elif type(document) is str:
            return document
        else:
            raise Exception("Param Type Error")

        
    def parseDocument(self, document, parent_doc=None):
        cssText = self.__getText(document)        
        cssParentText = self.__getText(parent_doc)
        self.cssText = cssParentText + "\n" + cssText
        self.cssSheet = cssutils.parseString(self.cssText)        
        # help(self.cssParentSheet)
        self.cssSheet
        for rule in self.cssSheet:
            if rule.type == 1:                    
                selector = rule.selectorList
                styles = rule.style
                self.dctSheet[selector] = styles
                for slc in selector.seq:
                    # help(styles)                
                    self.dctClasses[slc.selectorText]=styles
                    
    def getStyle(self, selector: str) -> CSSStyleDeclaration:
        return self.dctClasses.get(selector, None)


sheet = SheetCSS(css, parent_doc=css_)        
print((sheet.getStyle("body").backgroundImage))

    
# dct = {}
# sheet = cssutils.parseString(css)
# print("v", sheet.variables)
# # print(sheet.setSerializer())
# for rule in sheet:
#     print(rule.type)
#     # if rule.typeString != "COMMENT":
        
#     selector = rule.selectorList
#     styles = rule.style
#     dct[selector] = styles
#     # print(help(selector.seq[0]))

#     break
# pprint(dct)

# # from cssutils.tokenize2 import Tokenizer
# # tkn = Tokenizer()
# # for st in tkn.tokenize(css):
# #     print(st)
    