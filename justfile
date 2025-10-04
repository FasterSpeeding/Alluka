empty := shell('git submodule update', '--init', 'piped')

import? './piped/justfiles/python-all.just'
import? './piped/justfiles/mkdocs.just'
