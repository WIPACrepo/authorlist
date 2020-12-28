const insertScript = (path) =>
  new Promise((resolve, reject) => {
    const s = document.createElement('script');
    s.src = path;
    s.onload = () => resolve(s);  // resolve with script, not event
    s.onerror = reject;
    document.body.appendChild(s);
  });

var loadDeps = async function(baseurl){
    let scripts = [
      insertScript('https://cdn.jsdelivr.net/npm/vue@2.6.12'),
      insertScript('https://cdn.jsdelivr.net/npm/axios@0.21.0'),
    ]
    const s = document.createElement('link');
    s.rel = 'stylesheet';
    s.href = baseurl+'/static/external.css';
    document.head.appendChild(s);
    await Promise.all(scripts);
};

const authorlist_html = `
<h2 v-if="tag">{{ tag }}</h2>
<div class="authorlist_filters"><form v-on:submit.prevent="update" autocomplete="off">
  <div class="input vcenter"><label for="collab">Collaboration: </label><select name="collab" v-model="filters.collab">
    <option v-for="f in Object.keys(collab_options)" :value="f">{{ collab_options[f] }}</option>
  </select></div>
  <div class="input vcenter"><label for="date">Query Date: </label><input type="date" name="date" v-model="filters.date" /></div>
  <div class="input"><label for="formatting">Format: </label><select name="formatting" v-model="filters.formatting">
    <option v-for="f in Object.keys(formatting_options)" :value="f">{{ formatting_options[f] }}</option>
  </select></div>
  <div class="input vcenter"><input type="submit" /></div>
</form></div>
<div class="authorlist_body" v-if="fauthors">
  <h3>Author List</h3>
  <div class="intro_text" v-if="'intro_text' in fauthors" v-html="fauthors.intro_text"></div>
  <div v-if="fauthors.formatting == 'web'">
    <div class="authors">IceCube Collaboration: <span v-html="fauthors.authors"></span></div><hr>
    <ol class="institutions">
      <li v-for="name in fauthors.sorted_insts">{{ fauthors.insts[name]['cite'] }}</li>
    </ol>
    <ol class="thanks">
      <li v-for="name in fauthors.sorted_thanks">{{ fauthors.thanks[name] }}</li>
    </ol><hr>
    <div class="acknowledgements">
      <h2>Acknowledgements</h2>
      <span v-html="ack"></span>
    </div>
  </div>
  <div v-else><ul v-if="fauthors.formatting == 'web-institution'" class="authors-by-institution">
      <li v-for="name in fauthors.sorted_insts"><h4>{{ fauthors.insts[name]['cite'] }}</h4>
        <ul>
          <li v-for="author in fauthors.authors_by_inst[name]" v-html="author"></li>
        </ul>
      </li>
    </ul>
    <div v-else><div v-if="'wrap' in fauthors && fauthors.wrap" class="format_text_wrapper">
        <div id="data" class="format_text" v-html="fauthors.format_text"></div>
      </div>
      <div v-else class="format_text_wrapper">
        <pre id="data" class="format_text" v-html="fauthors.format_text"></pre>
      </div>
    </div>
  </div>
</div>
`;

let URLSerializer = function(p){
  let ret = [];
  for(const k in p){
    let v = p[k]
    if (v === null || typeof v === undefined)
      continue
    if (!Array.isArray(v)) {
      v = [v]
    }
    for(const vv of v){
      ret.push(encodeURIComponent(k)+'='+encodeURIComponent(vv))
    }
  }
  return ret.join('&')
};

async function AuthorList(id, baseurl = 'https://authorlist.icecube.wisc.edu', filters = {}) {
  await loadDeps(baseurl);

  var updateAuthors = async function(filters) {
    console.log('getting authors for filters:')
    console.log(filters)
    const response = await axios.get(baseurl+'/api/authors', {
      params: filters,
      paramsSerializer: URLSerializer
    });
    console.log('authors resp:')
    console.log(response.data)
    return response.data;
  };

  // get initial data from server
  let tag = ''
  filters = Object.assign({'formatting': 'web'}, filters)
  for(const v of window.location.hash.substring(1).split('&')){
    console.log(v)
    if (v.includes('=')) {
      let parts = v.split('=')
      if (parts[0] == 'collab' || parts[0] == 'date' || parts[0] == 'formatting') {
        filters[parts[0]] = parts[1]
      }
      else if (parts[0] == 'tag') {
        console.log('tagging:'+parts[1])
        tag = parts[1].replace('+', ' ')
      }
    }
  }
  let authors = await updateAuthors(filters);
  const authors_val = authors[Object.keys(authors)[0]];
  let filters_with_defaults = {
    collab: authors_val['title'],
    date: authors_val['date'],
    formatting: Object.keys(authors)[0],
  }
  console.log('tag='+tag)

  // write html
  if (id[0] == '#') {
    document.getElementById(id.substr(1)).innerHTML = authorlist_html;
  } else {
    console.error('bad id: '+id);
  }

  // start Vue
  var app = new Vue({
    el: id,
    data: {
      filters: filters_with_defaults,
      authors: authors,
      tag: tag,
      collab_options: {
        'IceCube': 'IceCube Collaboration',
        'IceCube-PINGU': 'IceCube/PINGU Collaboration',
        'IceCube-Gen2': 'IceCube-Gen2 Collaboration'
      },
      formatting_options: {'web': 'web', 'web-institution': 'web by institution'}
    },
    computed: {
      fauthors: function(){
        const keys = Object.keys(this.authors);
        if (keys.length > 0)
          return this.authors[keys[0]]
        return {}
      },
      ack: function(){
        if ('acks' in this.fauthors) {
          let ret = ''
          for (const ack of this.fauthors.acks) {
            ret += ' '+ack;
          }
          return ret;
        }
        return ''
      }
    },
    methods: {
      update: async function() {
        let params = JSON.parse(JSON.stringify( this.filters ));
        if (params.date != this.fauthors.date || params.collab != this.fauthors.title) {
          this.tag = ''
        }
        this.authors = await updateAuthors(params);
        // update location hash
        let hash = []
        for (const k in params) {
          hash.push(k+'='+params[k])
        }
        if (this.tag != '') {
          hash.push('tag='+this.tag.replace(' ', '+'))
        }
        window.location.hash = hash.join('&')
      }
    }
  });
}
