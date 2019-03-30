# blog应用的 views.py内编写：
from django.shortcuts import render, get_object_or_404
from .models import Post,Comment
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.generic import ListView

from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.contrib.postgres.search import TrigramSimilarity
from .forms import EmailPostForm, CommentForm, SearchForm

from django.core.mail import send_mail

from taggit.models import Tag

from django.db.models import Count, Avg, Sum, Min, Max

class PostListView(ListView):
    queryset = Post.published.all()
    context_object_name = 'posts'
    paginate_by = 3
    template_name = 'blog/post/list.html'

#def post_list(request, tag_slug=None):
#   tag = None
#    if tag_slug:
#        tag = get_object_or_404(Tag, slug=tag_slug)
#       object_list = object_list.filter(tags__in=[tag])
#    return render(request, 'blog/post/list.html', {'page': page, 'posts': posts,'tag':tag})

def post_list(request, tag_slug=None):
#def post_list(request):
    object_list = Post.published.all()
    tag = None

    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)
        object_list = object_list.filter(tags__in=[tag])
        
    paginator = Paginator(object_list, 3)  # 3 posts in each page
    page = request.GET.get('page')
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        #  if page is not an integer deliver the first page
        posts = paginator.page(1)
    except EmptyPage:
        #  if page is out of range deliver last page
        posts = paginator.page(paginator.num_pages)
    
    
#    return render(request, 'blog/post/list.html', {'page': page, 'posts': posts})
    return render(request, 'blog/post/list.html', {'page': page, 'posts': posts,'tag':tag})    


'''
def post_list(request):
        object_list = Post.published.all()
        paginator = Paginator(object_list, 3)  # 3 posts in each page
        page = request.GET.get('page')
        try:
            posts = paginator.page(page)
        except PageNotAnInteger:
            #  if page is not an integer deliver the first page
            posts = paginator.page(1)
        except EmptyPage:
            #  if page is out of range deliver last page
            posts = paginator.page(paginator.num_pages)
        return render(request, 'blog/post/list.html', {'page': page, 'posts': posts})
'''

        
def post_detail(request, year, month, day, post):
    post = get_object_or_404(Post, slug=post, status="published", publish__year=year, publish__month=month,
                             publish__day=day)
    # 列出这个post对应的所有活动的评论
    comments = post.comments.filter(active=True)
    new_comment = None

    if request.method == "POST":
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            # 通过表单直接建立新数据对象，但是不要保存到数据库中
            new_comment = comment_form.save(commit=False)
            # 因为外键还没有设置，现在设置外键为当前文章
            new_comment.post = post
            # 之后再保存该数据对象
            new_comment.save()
        # 数据验证不通过，则建立一个空白表单
    else:
        comment_form = CommentForm()
    
    post_tags_ids = post.tags.values_list('id',flat=True)
    similar_tags = Post.published.filter(tags__in=post_tags_ids).exclude(id=post.id)
    similar_posts = similar_tags.annotate(same_tags=Count('tags')).order_by('-same_tags','-publish')[:4]
# 修改render加上新的similar_posts
    return render(request, 'blog/post/detail.html',
              {'post': post, 'comments': comments, 'new_comment': new_comment, 'comment_form': comment_form,'similar_posts':similar_posts})

#    return render(request, 'blog/post/detail.html',
#                  {'post': post, 'comments': comments, 'new_comment': new_comment, 'comment_form': comment_form})


def post_share(request, post_id):
    # 通过id 拿 post对象
    post = get_object_or_404(Post, id=post_id, status='published')
    sent = False

    if request.method == "POST":
        # 提交表单是POST请求
        form = EmailPostForm(request.POST)
        #  如果验证通过，则发送邮件
        if form.is_valid():
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(post.get_absolute_url())
            subject = '{} ({}) recommends you reading "{}"'.format(cd['name'], cd['email'], post.title)
            message = 'Read "{}" at {}\n\n{}\'s comments:{}'.format(post.title, post_url, cd['name'], cd['comments'])
            send_mail(subject, message, 'witty98@126.com', [cd['to']])
            sent = True

    else:
        # 如果是GET请求，就用表单返回页面
        form = EmailPostForm()
    return render(request, 'blog/post/share.html', {'post': post, 'form': form, 'sent': sent})

def post_search(request):
    form = SearchForm()
    query = None
    results = []
    if 'query' in request.GET:
        form = SearchForm(request.GET)
        if form.is_valid():
            query = form.cleaned_data['query']
            #results = Post.objects.annotate(search=SearchVector('title', 'slug', 'body'), ).filter(search=query)
            #search_vector = SearchVector('title', 'body')
            
            search_vector = SearchVector('title', weight='A') + SearchVector('body', weight='B')
            search_query = SearchQuery(query)
            #results = Post.objects.annotate(
            #    search=search_vector,
            #    rank=SearchRank(search_vector, search_query)
            #).filter(rank__gte=0.33).order_by('-rank')

            results = Post.objects.annotate(
              similarity=TrigramSimilarity('title',query),
              ).filter(similarity__gte=0.1).order_by('-similarity')

            #results = Post.objects.annotate(
            #    search=search_vector,
            #    rank=SearchRank(search_vector, search_query)
            #).filter(search=search_query).order_by('-rank')

    return render(request, 'blog/post/search.html', {'query': query, "form": form, 'results': results})

