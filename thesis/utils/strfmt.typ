#let strfmt(fmt, ..args) = {
  let positional = args.pos()
  let named = args.named()
  let parts = ()
  let last-end = 0
  
  for m in fmt.matches(regex("\{([a-zA-Z0-9_\-]+)\}")) {
    parts.push(fmt.slice(last-end, m.start))
    let key = m.captures.at(0)
    
    let val = ""
    if key.match(regex("^\d+$")) != none {
      let idx = int(key)
      assert(idx < positional.len(), message: "Insufficient positional arguments for index {" + key + "}")
      val = str(positional.at(idx))
    } else {
      assert(key in named, message: "Missing named argument {" + key + "}")
      val = str(named.at(key))
    }
    
    parts.push(val)
    last-end = m.end
  }
  
  parts.push(fmt.slice(last-end))
  
  return parts.join("")
}