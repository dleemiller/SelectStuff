# Flow

1. ApplicationStuff class is instantiated for each applicaiton.
  i.e. applications/news/news.py
2. Each application has it's own 
  1. Models
  2. states dir for DSPy optimized pickle files.
  3. config.yml to define things like endpoints, tags, etc
    TODO: Add LM.kwargs overrides(provider specific, ie aws_region_name), and lm.args(dspy specific, ie num_retries) overrides
  4. dspy signature, this defines the dspy.InputField and dspy.OutputField attributes. 
    
