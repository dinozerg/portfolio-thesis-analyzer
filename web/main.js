'use strict';
const $ = id => document.getElementById(id);
const COLORS = ['#a5b1cd','#eda18f','#8093b4','#d4d16b','#e58e87','#54a5a3','#efbf6e','#b49abc','#8fb4ae','#b6bfce'];
let state = {holdings:[{symbol:'AAPL',name:'Apple Inc.'},{symbol:'MSFT',name:'Microsoft Corporation'},{symbol:'SPY',name:'SPDR S&P 500 ETF Trust'}],weights:[3334,3333,3333],period:'5y',risk_free:0};
let busy = false, searchTimer, searchVersion = 0, searchController, draftWeights=null;
let pinnedLine=null, hoveredLine=null;
let dateDraft=false, recentlyAdded=null;
function localToday(){const now=new Date();return [now.getFullYear(),String(now.getMonth()+1).padStart(2,'0'),String(now.getDate()).padStart(2,'0')].join('-');}
const percent = (v, signed=false) => v == null ? 'N/A' : (signed && v>0?'+':'')+(v*100).toFixed(2)+'%';
const compactPercent = v => (v>0?'+':'')+(v*100).toFixed(1)+'%';
const metricValue = (name,v) => v == null ? 'N/A' : name === 'Sharpe ratio' ? v.toFixed(2) : percent(v);
const money=new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0});
const unitMoney=new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',minimumFractionDigits:2,maximumFractionDigits:2});
function renderInvestmentSummary(){
  renderJourney();
  const starting=10000,portfolioEnd=state.portfolio.at(-1)*starting,benchmarkEnd=state.benchmark.at(-1)*starting;
  [['portfolio',portfolioEnd,state.metrics['Total return']],['benchmark',benchmarkEnd,state.benchmark_metrics['Total return']]].forEach(([id,ending,ret])=>{
    $(id+'-value').textContent=money.format(ending);
    const gain=ending-starting,roundedGain=Math.round(gain),node=$(id+'-profit');
    node.className=gain>0?'positive':gain<0?'negative':'';
    node.textContent=roundedGain===0?'No change to the nearest dollar ('+percent(ret,true)+')':(gain>0?'You gained ':'You lost ')+money.format(Math.abs(gain))+' ('+percent(ret,true)+')';
  });
  const difference=Math.round(portfolioEnd)-Math.round(benchmarkEnd);
  $('dollar-comparison').textContent=Math.round(difference)===0?'Your portfolio and SPY finished at the same value to the nearest dollar.':'Your portfolio finished '+money.format(Math.abs(difference))+(difference>0?' ahead of':' behind')+' SPY on the same $10,000 starting investment.';
  const dateFormat=new Intl.DateTimeFormat('en-US',{month:'short',day:'numeric',year:'numeric'});
  $('summary-dates').textContent=dateFormat.format(new Date(state.dates[0]+'T12:00:00'))+' – '+dateFormat.format(new Date(state.dates.at(-1)+'T12:00:00'))+' · Historical illustration, not a forecast · Dollar amounts rounded; before fees and taxes';
  $('unit-example').textContent='Every line starts at $1. Your portfolio ended at '+unitMoney.format(state.portfolio.at(-1))+'.';
}
function element(tag,className,text){const node=document.createElement(tag);if(className)node.className=className;if(text!=null)node.textContent=text;return node;}
function showError(message){$('error').textContent=message;$('error').hidden=!message;}
function busyState(value){busy=value;document.body.classList.toggle('busy',value);document.querySelectorAll('button,input,select').forEach(n=>n.disabled=value);}
function hideSearch(){searchVersion++;if(searchController)searchController.abort();$('search-results').hidden=true;$('stock-search').setAttribute('aria-expanded','false');}
async function requestPortfolio(action=null, overrides={}, message='Updating portfolio…'){
  if(busy)return false;
  hideSearch();busyState(true);showError('');$('status').textContent=message;
  $('add-feedback').hidden=action?.type!=='add';
  if(action?.type==='add')$('add-feedback').textContent='Adding '+action.holding.symbol+' to the chart…';
  const payload={holdings:state.holdings,weights:state.weights,period:state.period,start_date:state.start_date,end_date:state.end_date,risk_free:state.risk_free,...overrides,action};
  let success=false;
  try{
    const response=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:AbortSignal.timeout(180000)});
    const result=await response.json();if(!response.ok)throw new Error(result.error || 'Could not update this portfolio.');
      state=result;draftWeights=null;dateDraft=false;recentlyAdded=action?.type==='add'?action.holding.symbol:null;
      if(action?.type==='random')$('selection-story').textContent='These stocks were picked randomly from a fixed 30-stock US equity list, with equal starting allocations. This is an experiment in diversification; there is no investor-specific investment thesis behind the picks.';
      if(action?.type==='add'||action?.type==='remove')$('selection-story').textContent='You edited this mix. The app measures its history, but does not know why you chose these holdings. Record your goal and reasoning below.';
    if(recentlyAdded)pinnedLine=recentlyAdded;
    render();success=true;
    const notices={add:'Stock added. Existing allocations scaled proportionally.',remove:'Holding removed. Remaining allocations redistributed proportionally.',weights:'Your exact starting allocations are now applied.',equal:'Starting allocations reset to equal weights.',random:'New random mix generated with equal starting weights.',refresh:'Prices refreshed.'};
    $('status').textContent=notices[action?.type] || 'Ready · Edit any allocation or add another stock.';
    if(recentlyAdded){
      const i=state.holdings.findIndex(h=>h.symbol===recentlyAdded);
      const message='✓ '+recentlyAdded+' added to the chart · '+(state.weights[i]/100).toFixed(2)+'% starting allocation. Its line is highlighted.';
      $('add-feedback').hidden=true;$('status').textContent=message;
      document.querySelector('.chart-panel').scrollIntoView({behavior:'smooth',block:'nearest'});
    }
  }catch(error){
    showError(error.name==='TimeoutError'?'The data provider took too long. Please retry. Your last portfolio is unchanged.':error.message);
    $('status').textContent='Update failed. Your last portfolio is unchanged.';
    if(!dateDraft)resetHistoryControls();
    if(action?.type==='add')$('add-feedback').textContent='Could not add '+action.holding.symbol+'. Your chart and allocations are unchanged.';
    $('risk-free').value=(state.risk_free*100).toFixed(2);
    if(state.dates)renderHoldings();
  }finally{busyState(false);applyUIConstraints();}
  return success;
}
function swatch(color,dashed=false){let s=element('span','swatch');if(dashed){s.style.background='none';s.style.borderTop='2px dashed #15233e';s.style.height='0';}else s.style.background=color;return s;}
function lineButton(name,label,color,dashed=false){
  const button=element('button','line-button');button.type='button';button.dataset.line=name;
  button.setAttribute('aria-label','Highlight '+name);button.setAttribute('aria-pressed',String(pinnedLine===name));
  button.append(swatch(color,dashed),document.createTextNode(label));
  button.addEventListener('mouseenter',()=>hoverLine(name));button.addEventListener('mouseleave',()=>hoverLine(null));
  button.addEventListener('focus',()=>hoverLine(name));button.addEventListener('blur',()=>hoverLine(null));
  button.addEventListener('click',()=>pinLine(name));return button;
}
function lineDisplayName(name){const holding=state.holdings.find(h=>h.symbol===name);return holding?name+' · '+holding.name:name==='SPY benchmark'?'SPY · SPDR S&P 500 ETF Trust (benchmark)':name;}
function hoverLine(name){hoveredLine=name;paintLineFocus();}
function pinLine(name){pinnedLine=pinnedLine===name?null:name;hoveredLine=null;paintLineFocus();}
function clearLineFocus(){pinnedLine=null;hoveredLine=null;paintLineFocus();}
function paintLineFocus(){
  const chart=$('performance-chart');if(!chart.data)return;
  const active=pinnedLine||hoveredLine;
  document.querySelectorAll('.line-button').forEach(button=>{
    button.setAttribute('aria-pressed',String(pinnedLine===button.dataset.line));
    button.closest('tr').classList.toggle('highlighted-row',active===button.dataset.line);
  });
  $('clear-highlight').hidden=!pinnedLine;
  const trace=chart.data.find(t=>t.name===active);
  $('line-focus').textContent=trace?(pinnedLine?'Selected: ':'Highlighting: ')+lineDisplayName(trace.name)+' · '+compactPercent(trace.y.at(-1)-1)+' over this period':'Hover a line to highlight it. Click a line or ticker to keep it selected.';
  // Style the rendered SVG without redrawing Plotly: a redraw during hover
  // emits unhover and can interrupt the subsequent click on that same line.
  chart.data.forEach(trace=>{
    const group=chart.querySelector('.scatterlayer .trace'+CSS.escape(trace.uid));if(!group)return;
    const selected=trace.name===active;
    group.style.opacity=!active||selected?'1':'.16';
    group.querySelectorAll('.js-line').forEach(path=>{path.style.strokeWidth=(selected?(trace.name==='Portfolio'?7:4):trace.line.width)+'px';});
  });
}
function bindLineInteractions(){
  const chart=$('performance-chart');
  if(!chart.lineInteractionsBound){
    chart.on('plotly_hover',event=>hoverLine(event.points[0]?.data.name||null));
    chart.on('plotly_unhover',()=>hoverLine(null));
    chart.on('plotly_click',event=>{const name=event.points[0]?.data.name;if(name)pinLine(name);});
    chart.on('plotly_afterplot',paintLineFocus);
    chart.addEventListener('mouseleave',()=>hoverLine(null));chart.lineInteractionsBound=true;
  }
  if(!chart.data.some(t=>t.name===pinnedLine))pinnedLine=null;
  hoveredLine=null;paintLineFocus();
}
function renderHoldings(){
  const body=$('holding-rows');body.replaceChildren();
  const total=element('tr','portfolio-row');let name=element('td');name.append(lineButton('Portfolio','Portfolio','#b51235'));total.append(name,element('td',null,'100%'),element('td',state.metrics['Total return']>=0?'positive':'negative',compactPercent(state.metrics['Total return'])),element('td'));body.append(total);
  state.holdings.forEach((holding,i)=>{
    const row=element('tr');let label=element('td');label.title=holding.name;label.append(lineButton(holding.symbol,holding.symbol,COLORS[i%COLORS.length]));
    label.append(element('small','company-name',holding.name));
    if(holding.symbol===recentlyAdded)label.append(element('span','new-badge','NEW'));
    const weight=element('td');const field=element('label','weight-field');const input=element('input');input.type='number';input.min='0';input.max='100';input.step='0.01';input.value=((draftWeights||state.weights)[i]/100).toFixed(2);input.setAttribute('aria-label',holding.symbol+' allocation percent');
    input.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();input.blur();}if(event.key==='Escape'){$('cancel-weights').click();}});
    input.addEventListener('input',()=>{
      if(!draftWeights)draftWeights=[...state.weights];
      draftWeights[i]=input.value.trim()!==''&&input.checkValidity()?Math.round(Number(input.value)*100):null;
      updateDraft();
    });
    field.append(input,document.createTextNode('%'));weight.append(field);
    const ret=state.series[holding.symbol].at(-1)-1;
    const removal=element('td');const remove=element('button','remove-button','×');remove.setAttribute('aria-label','Remove '+holding.symbol);remove.title='Remove '+holding.symbol;remove.disabled=state.holdings.length===1;remove.addEventListener('click',()=>requestPortfolio({type:'remove',index:i}));removal.append(remove);
    row.append(label,weight,element('td',ret>=0?'positive':'negative',compactPercent(ret)),removal);body.append(row);
  });
  let row=element('tr','benchmark-row'),label=element('td');label.append(lineButton('SPY benchmark','SPY benchmark','#15233e',true));row.append(label,element('td',null,'—'),element('td',null,compactPercent(state.benchmark_metrics['Total return'])),element('td'));body.append(row);
  $('holding-count').textContent=state.holdings.length+(state.holdings.length===1?' holding':' holdings');updateDraft();
}
function updateDraft(){
  const weights=draftWeights||state.weights,total=weights.reduce((a,b)=>a+(b||0),0),valid=weights.every(w=>w!==null)&&total===10000;
  $('allocation-total').textContent=(total/100).toFixed(2)+'%'+(draftWeights?' · draft':'');
  $('allocation-total').classList.toggle('negative',!valid);
  $('weight-actions').hidden=!draftWeights;
  $('apply-weights').disabled=busy||!valid;
  $('weight-help').textContent=draftWeights?(valid?'Ready to apply. The chart still shows your last applied weights.':'Draft weights must total 100%. The chart still shows your last applied weights.'):'Edit the starting percentages, then apply when they total 100%.';
  if(draftWeights){
    $('status').textContent='Unapplied allocation edits · chart and risk measures are unchanged.';
    ['random-button','equal-button','custom-dates','stock-search','risk-free','refresh-button','start-date','end-date','apply-range','cancel-range'].forEach(id=>$(id).disabled=true);
    document.querySelectorAll('.period-preset').forEach(button=>button.disabled=true);
    document.querySelectorAll('.remove-button').forEach(n=>n.disabled=true);
  }
}
function resetHistoryControls(){
  $('start-date').value=state.start_date||state.dates?.[0]||'';
  $('end-date').value=state.end_date||state.dates?.at(-1)||localToday();
  updateDateDraft();
}
function updateDateDraft(){
  const start=$('start-date'),end=$('end-date');
  const custom=state.period==='custom'||dateDraft;
  document.querySelectorAll('.period-preset').forEach(button=>button.setAttribute('aria-pressed',String(!custom&&button.dataset.period===state.period)));
  $('custom-dates').setAttribute('aria-pressed',String(custom));
  start.readOnly=end.readOnly=!custom;
  $('date-actions').hidden=!custom;
  start.max=end.max=localToday();
  const valid=start.value&&end.value&&start.checkValidity()&&end.checkValidity()&&start.value<end.value;
  $('apply-range').disabled=busy||!!draftWeights||!dateDraft||!valid;
  $('cancel-range').hidden=!dateDraft;
  $('date-help').textContent=dateDraft?(valid?'Click Apply range to update the chart. It still shows the last applied dates.':'Choose a start date before the end date. Neither can be in the future. The chart is unchanged.'):custom?'Both dates included. Trading days only.':'Applied trading dates for '+Number(state.period[0])+(state.period==='1y'?' year.':' years.')+' Choose Custom dates to edit.';
  if(dateDraft){
    ['random-button','equal-button','stock-search','risk-free','refresh-button','apply-weights'].forEach(id=>$(id).disabled=true);
    document.querySelectorAll('.weight-field input,.remove-button').forEach(n=>n.disabled=true);
  }
}
function applyUIConstraints(){
  busyState(busy);updateDraft();updateDateDraft();
  if(state.holdings.length===1)document.querySelectorAll('.remove-button').forEach(n=>n.disabled=true);
}
function render(){
  const n=state.holdings.length, years=Number(state.period[0]);
  $('stock-count').value=n;
  const equal=Math.max(...state.weights)-Math.min(...state.weights)<=1;
  $('intro').replaceChildren(document.createTextNode('The thick '),element('span','red','red line'),document.createTextNode(' is your '+(equal&&n>1?'equally weighted ':'')+'portfolio of '),element('strong',null,String(n)),document.createTextNode((n===1?' holding.':' holdings.')+' Thin lines show the holdings; the dashed line is SPY.'));
  $('chart-title').textContent=state.period==='custom'?'Growth of $1 · Selected Dates':'Growth of $1 Over '+years+(years===1?' Year':' Years');$('return-heading').textContent=state.period==='custom'?'RETURN':years+'Y RETURN';
  renderInvestmentSummary();
  resetHistoryControls();$('date-label').textContent=state.dates[0]+' — '+state.dates.at(-1)+' · '+state.dates.length.toLocaleString()+' observations';
  $('add-notice').hidden=!recentlyAdded;
  if(recentlyAdded){const i=state.holdings.findIndex(h=>h.symbol===recentlyAdded);$('add-notice').replaceChildren(swatch(COLORS[i%COLORS.length]),document.createTextNode('✓ '+recentlyAdded+' added to your chart and portfolio · '+(state.weights[i]/100).toFixed(2)+'% starting allocation.'));}
  $('correlation-value').textContent=state.correlation==null?'—':state.correlation.toFixed(2);
  $('correlation-explanation').textContent=state.correlation==null?'Needs at least two holdings with positive allocations.':'How closely the holdings’ daily returns move together.';
  positionBadges();
  const warnings=[];if(n<3)warnings.push('Add at least three stocks or ETFs for the assignment portfolio.');
  if(state.metadata.cached_fallback)warnings.push('Provider unavailable: showing a previously downloaded dataset from '+state.metadata.retrieved_utc+'.');
  if(state.dropped>1)warnings.push(state.dropped+' incomplete observations excluded. All holdings and SPY use the same remaining dates.');
  $('data-warning').textContent=warnings.join(' ');$('data-warning').hidden=!warnings.length;
  renderHoldings();
  const hovertemplate='<b>%{meta}</b><br>%{x|%b %d, %Y}<br>Value of $1 invested: $%{y:.2f}<br>Return since start: %{customdata:+.2%}<extra></extra>';
  const traces=state.holdings.map((h,i)=>({type:'scatter',mode:'lines',x:state.dates,y:state.series[h.symbol],name:h.symbol,line:{color:COLORS[i%COLORS.length],width:1.6},hovertemplate}));
  traces.push({type:'scatter',mode:'lines',x:state.dates,y:state.benchmark,name:'SPY benchmark',line:{color:'#728093',width:1.7,dash:'dash'},hovertemplate});
  traces.push({type:'scatter',mode:'lines',x:state.dates,y:state.portfolio,name:'Portfolio',line:{color:'#b51235',width:6},hovertemplate});
  traces.forEach(trace=>{trace.meta=lineDisplayName(trace.name);trace.customdata=trace.y.map(value=>value-1);trace.opacity=1;trace.uid='line-'+trace.name.replaceAll(' ','-');});
  const small=window.innerWidth<650;
  const days=(new Date(state.dates.at(-1))-new Date(state.dates[0]))/86400000;
  Plotly.react('performance-chart',traces,{margin:{l:small?48:70,r:12,t:10,b:38},autosize:true,showlegend:false,paper_bgcolor:'white',plot_bgcolor:'white',font:{family:'Segoe UI, Arial, sans-serif',color:'#77818c',size:small?11:14},hovermode:'closest',hoverdistance:15,dragmode:false,clickmode:'event',hoverlabel:{bgcolor:'#fff',font:{size:12}},xaxis:{gridcolor:'#edf0f3',linecolor:'#c7cdd5',showline:true,zeroline:false,tickformat:days<90?'%b %d':days<730?'%b %Y':'%Y',nticks:small?4:6},yaxis:{title:small?undefined:{text:'Value of $1 invested',standoff:18},gridcolor:'#edf0f3',tickprefix:'$',tickformat:'.2f',zeroline:false,rangemode:'tozero'},uirevision:state.period+state.dates[0]+state.dates.at(-1)+state.holdings.map(h=>h.symbol).join(',')},{responsive:true,displayModeBar:false,displaylogo:false,doubleClick:false,scrollZoom:false}).then(bindLineInteractions);
  const metrics=$('metrics');metrics.replaceChildren();
  const helps=['Total change over the selected period','Sample daily volatility × √252','Excess return per unit of volatility','Largest loss from a previous peak'];
  Object.entries(state.metrics).forEach(([key,value],i)=>{let node=element('div','metric');node.append(element('p',null,key),element('strong',null,metricValue(key,value)),element('small',null,helps[i]));metrics.append(node);});
  Plotly.react('allocation-chart',[{type:'pie',labels:state.holdings.map(h=>h.symbol),values:state.weights,hole:.68,sort:false,marker:{colors:state.holdings.map((_,i)=>COLORS[i%COLORS.length])},textinfo:n<=10?'label+percent':'none',textfont:{size:12},hovertemplate:'%{label}: %{percent}<extra></extra>'}],{margin:{l:50,r:50,t:15,b:15},paper_bgcolor:'white',showlegend:false,font:{color:'#677687'},annotations:[{text:'100%',showarrow:false,font:{size:24,color:'#15233e'}}]},{responsive:true,displayModeBar:false});
  const comparison=$('comparison-rows');comparison.replaceChildren();
  Object.keys(state.metrics).forEach(key=>{let row=element('tr');row.append(element('td',null,key),element('td',null,metricValue(key,state.metrics[key])),element('td',null,metricValue(key,state.benchmark_metrics[key])));comparison.append(row);});
  $('investment-example').textContent='A $10,000 starting investment would be worth '+money.format(state.portfolio.at(-1)*10000)+' in this portfolio or '+money.format(state.benchmark.at(-1)*10000)+' in SPY. Sharpe assumes '+(state.risk_free*100).toFixed(2)+'% annual risk-free return.';
  $('source-meta').textContent='Retrieved '+state.metadata.retrieved_utc+' (UTC). '+state.dropped+' incomplete observations excluded. Requests cached for one hour. Search: Yahoo Finance company/ticker database. Random mixes: fixed 30-stock US equity universe.';
}
async function doSearch(){
  const query=$('stock-search').value.trim();hideSearch();if(!query || busy || dateDraft || draftWeights)return;
  const version=searchVersion;searchController=new AbortController();const results=$('search-results');
  results.replaceChildren(element('div','search-message','Searching Yahoo Finance…'));results.hidden=false;$('stock-search').setAttribute('aria-expanded','true');
  try{
    const response=await fetch('/api/search?q='+encodeURIComponent(query),{signal:searchController.signal});const payload=await response.json();if(version!==searchVersion)return;if(!response.ok)throw new Error(payload.error);
    results.replaceChildren();if(!payload.results.length)results.append(element('div','search-message','No supported US stocks or ETFs found. Try a company name or ticker.'));
    payload.results.forEach(result=>{
      const button=element('button');button.type='button';const content=element('span');content.append(element('strong',null,result.symbol),element('small',null,result.name),element('small',null,result.exchange+' · '+result.type));
      const present=state.holdings.some(h=>h.symbol===result.symbol);button.append(content,element('span','result-add',present?'✓ Added':'+ Add'));button.disabled=present;button.setAttribute('aria-label',present?result.symbol+' already added':'Add '+result.symbol+' '+result.name+' to chart');
      button.addEventListener('click',async()=>{const ok=await requestPortfolio({type:'add',holding:{symbol:result.symbol,name:result.name}}, {}, 'Adding '+result.symbol+' and checking its history…');if(ok)$('stock-search').value='';});
      results.append(button);
    });
  }catch(error){if(error.name==='AbortError'||version!==searchVersion)return;results.replaceChildren(element('div','search-message',error.message||'Search unavailable. Please retry.'));}
}
$('stock-search').addEventListener('input',()=>{clearTimeout(searchTimer);hideSearch();searchTimer=setTimeout(doSearch,350);});
$('stock-search').addEventListener('keydown',event=>{if(event.key==='Escape')hideSearch();if(event.key==='Enter'){event.preventDefault();clearTimeout(searchTimer);doSearch();}if(event.key==='ArrowDown'){event.preventDefault();$('search-results').querySelector('button:not(:disabled)')?.focus();}});
document.addEventListener('click',event=>{if(!event.target.closest('.search-section'))hideSearch();});
function positionBadges(){
  const slider=$('stock-count'),n=Number(slider.value),ratio=(Number(slider.max)-n)/(Number(slider.max)-Number(slider.min));
  $('count-value').value=n;$('random-size').textContent=n===1?'1 stock · 100% allocation':n+' stocks · equal weights';
  const actual=state.holdings.length;
  $('count-help').textContent=n===actual?actual+(actual===1?' holding':' holdings')+' in your portfolio. Move the slider to size a new random mix.':'Portfolio: '+actual+'. Next random mix: '+n+'. Click Generate random mix to replace it.';
  if(window.innerWidth>650){$('count-value').style.top=(slider.offsetTop+15+ratio*(slider.clientHeight-30)-$('count-value').clientHeight/2)+'px';}
  else $('count-value').style.top='28px';
}
$('stock-count').addEventListener('input',positionBadges);
$('clear-highlight').addEventListener('click',clearLineFocus);
document.addEventListener('keydown',event=>{if(event.key==='Escape')clearLineFocus();});
window.addEventListener('resize',positionBadges);
$('random-button').addEventListener('click',()=>requestPortfolio({type:'random',count:Number($('stock-count').value)}, {}, 'Generating a random mix and loading prices…'));
$('equal-button').addEventListener('click',()=>requestPortfolio({type:'equal'}));
$('apply-weights').addEventListener('click',()=>requestPortfolio({type:'weights',weights:[...draftWeights]}, {}, 'Applying your allocations…'));
$('cancel-weights').addEventListener('click',()=>{draftWeights=null;renderHoldings();applyUIConstraints();$('status').textContent='Allocation edits cancelled. Showing applied weights.';});
document.querySelectorAll('.period-preset').forEach(button=>button.addEventListener('click',()=>{
  dateDraft=false;requestPortfolio(null,{period:button.dataset.period,start_date:null,end_date:null},'Loading the selected history…');
}));
$('custom-dates').addEventListener('click',()=>{dateDraft=true;hideSearch();applyUIConstraints();$('start-date').focus();});
['start-date','end-date'].forEach(id=>$(id).addEventListener('input',()=>{dateDraft=true;applyUIConstraints();}));
$('apply-range').addEventListener('click',()=>requestPortfolio(null,{period:'custom',start_date:$('start-date').value,end_date:$('end-date').value},'Loading your selected date range…'));
$('cancel-range').addEventListener('click',()=>{dateDraft=false;resetHistoryControls();applyUIConstraints();});
$('risk-free').addEventListener('change',()=>{if(!$('risk-free').checkValidity()||$('risk-free').value===''){showError('Enter a risk-free assumption from 0 to 20%.');return;}requestPortfolio(null,{risk_free:Number($('risk-free').value)/100});});
$('refresh-button').addEventListener('click',()=>requestPortfolio({type:'refresh'}, {},'Refreshing historical prices…'));
requestPortfolio(null,{},'Loading historical prices…');

function renderJourney(){
  const v=state.portfolio,d=state.dates;
  let peak=0,worstPeak=0,trough=0,dd=0;
  for(let i=1;i<v.length;i++){if(v[i]>=v[peak])peak=i;const decline=v[i]/v[peak]-1;if(decline<dd){dd=decline;worstPeak=peak;trough=i;}}
  const fmt=i=>new Date(d[i]+'T12:00:00').toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'});
  const first=v.findIndex((x,i)=>i>0&&x>1);
  let lastBelow=-1;v.forEach((x,i)=>{if(x<1)lastBelow=i;});
  $('journey').textContent=first<0?'This portfolio never rose above its starting value during the selected history.':'It first exceeded your starting money on '+fmt(first)+'. '+(v.at(-1)<1?'It finished below your starting money.':lastBelow>=0?'After its last dip below the starting amount, it returned above that level on '+fmt(lastBelow+1)+' and stayed at or above it through the end.':'It never closed below the starting amount in this window.');
  $('downside').textContent=dd===0?'There was no decline between observed closing values in this window.':'The hardest fall was '+percent(Math.abs(dd))+' from '+fmt(worstPeak)+' to '+fmt(trough)+'. Your original $10,000 would have fallen from '+money.format(v[worstPeak]*10000)+' at that peak to '+money.format(v[trough]*10000)+'. This is a loss from a previous high, not necessarily from your original investment.';
  const recovered=v.findIndex((x,i)=>i>trough&&x>=v[worstPeak]);
  $('recovery').textContent=dd===0?'':recovered<0?'It had not recovered that peak by the end of the selected history.':'It regained that previous peak on '+fmt(recovered)+'. The gain at the end required staying invested through that decline.';
  renderTolerance();
}
function renderTolerance(){
  const input=$('loss-tolerance'),limit=Number(input.value);
  if(!input.value||!input.validity.valid){$('tolerance-result').textContent='Enter a limit from 0% to 100% to compare with the historical decline.';return;}
  const loss=Math.abs(state.metrics['Maximum drawdown'])*100;
  $('tolerance-result').textContent='Your stated limit: '+limit+'%. Historical peak-to-trough loss: '+loss.toFixed(2)+'%. '+(loss>limit?'This history exceeded your limit.':'This history stayed within your limit, but future losses could exceed it.')+' This comparison does not establish suitability.';
}
$('loss-tolerance').addEventListener('input',()=>{if(state.metrics)renderTolerance();});
