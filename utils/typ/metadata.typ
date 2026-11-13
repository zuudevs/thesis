#let meta = json("metadata.json")

#let make-fullname(person: dictionary) = {
	assert("first_name" in person.keys(), message: "must have first_name key!")
	assert("middle_name" in person.keys(), message: "must have middle_name key!")
	assert("last_name" in person.keys(), message: "must have last_name key!")

	return person.first_name + if person.middle_name != none {
		" " + person.middle_name
	} else {
		""
	} + if person.last_name != none {
		" " + person.last_name
	} else {
		""
	}
}

#let format-person(person) = {
  if person == none { return "" }
  let p = if person.at("prefixes", default: none) != none and person.prefixes.len() > 0 {
    person.prefixes.join(" ") + " "
  } else { "" }
  
  let s = if person.at("suffixes", default: none) != none and person.suffixes.len() > 0 {
    ", " + person.suffixes.join(", ")
  } else { "" }

	let name = if person.first_name == none { "" } else { person.first_name }
	name += if person.middle_name == none { "" } else { " " + person.middle_name }
	name += if person.last_name == none { "" } else { " " + person.last_name }

  return p + name + s
}

#let abbreviate-name(name : str, count: int) = {
	assert(name.len() > 0, message: "length name must upper 0!")
	assert(count > 0, message: "abbreviate count can not be negative!")
	
	let words = name.split(" ")

	assert(words.len() > count, message: "abbreviate count greater than words count!")

	let reversed_word = words.rev()
	let chars = ()

	for (i, w) in reversed_word.enumerate() {
		chars.push(if i < count { w.first() + "." } else { w })
	}

	return chars.rev().join(" ")
}

#make-fullname(person: meta.student)