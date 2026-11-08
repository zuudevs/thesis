#let simplify_name(name: str, count: int) = {
	let words = name.split(" ")
	let revWords = words.rev()
	let abbr = ()
	for word in revWords.slice(0, count) {
		abbr.push(word.at(0))
	}
	let res = abbr.map(it => it + ".")
	return (res + revWords.slice(count, revWords.len())).rev().join(" ")	
}